import decimal
import json
import random
import re
import string
import time
import uuid
import datetime
from datetime import date, timedelta
from functools import wraps
from math import ceil
from typing import Dict, Optional, TypeVar, Union
from uuid import UUID, uuid4

import phonenumbers
import requests
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AnonymousUser
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.db.models import TextChoices
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.html import strip_tags
from django.utils.text import slugify
from django.utils.timezone import is_aware, make_aware
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserTypes
from core.decorators import CustomApiPermissionRequired
from core.errors.app_errors import OperationError
from services.cache_util import CacheUtil
from services.encryption_util import AESCipher
from services.log import AppLogger

T = TypeVar("T")


class HTTPMethods(TextChoices):
    get = "GET"
    post = "POST"
    patch = "PATCH"
    put = "PUT"
    options = "OPTIONS"
    delete = "DELETE"


class AnalyticsDuration(TextChoices):
    Daily = "daily"
    Weekly = "weekly"
    Monthly = "monthly"
    Quarterly = "quarterly"
    Yearly = "yearly"


class CustomAPIResponseUtil:
    encrypt_response = False
    app_enc_enabled = settings.APP_ENC_ENABLED

    def response_with_json(self, data, status_code=None):
        if not status_code:
            status_code = status.HTTP_200_OK

        if not data:
            data = {}
        elif not isinstance(data, dict):
            data = {"data": data}

        if not self.app_enc_enabled and not self.encrypt_response:
            return Response(data, status=status_code)

        cipher = AESCipher(settings.APP_ENC_KEY, settings.APP_ENC_VEC)
        encrypted_data = cipher.encrypt_nested(data)

        return Response(encrypted_data, status=status_code)

    def response_with_error(self, error_list, status_code=None):
        if not status_code:
            status_code = status.HTTP_400_BAD_REQUEST

        response_errors = {"non_field_errors": []}

        def extract_errors(error_detail):
            if isinstance(error_detail, str):
                response_errors["non_field_errors"].append(error_detail)
            elif isinstance(error_detail, dict):
                for key, value in error_detail.items():
                    response_errors[key] = value if isinstance(value, list) else [value]

        if isinstance(error_list, list):
            for error in error_list:
                extract_errors(error)
        else:
            extract_errors(error_list)

        if not response_errors["non_field_errors"]:
            response_errors.pop("non_field_errors")

        return self.response_with_json(response_errors, status_code=status_code)

    def bad_request(self, message=None, data: dict = None):
        if not data:
            data = {}
        elif not isinstance(data, dict):
            data = {"data": data}

        if message:
            data["message"] = message

        return self.response_with_json(
            {"error": data}, status_code=status.HTTP_400_BAD_REQUEST
        )

    def response_with_message(self, message, status_code=status.HTTP_200_OK):
        return self.response_with_json({"message": message}, status_code=status_code)

    def validation_error(self, errors, status_code=None):
        if status_code is None:
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

        if isinstance(errors, dict) and "error" in errors:
            nested_errors = errors.pop("error")
            errors.pop("status_code", None)
            for key, value in nested_errors.items():
                errors.update({key: [value]})
        return self.response_with_json({"errors": errors}, status_code=status_code)


class Util:
    @staticmethod
    def is_valid_password(password):
        return re.match(
            r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@#$%^&+=!]).{8,}$", password
        )

    @staticmethod
    def get_user_with_roles(user):
        def _user_data_source_callback():
            _data = {
                "id": user.id,
                "permissions": list(user.user_permissions_id()),
                "roles": list(user.roles.values_list("id", flat=True)),
            }
            return _data, None

        if user:
            util = CacheUtil()
            cache_key = util.generate_cache_key(
                user.pk, user.tenant_id, "roles", "permissions"
            )
            data, _ = util.get_cache_value_or_default(
                cache_key, _user_data_source_callback
            )
            return data
        else:
            return {"id": None, "permissions": [], "roles": []}

    @staticmethod
    def generate_digits(length):
        digits = "0123456789"
        code = ""
        for _ in range(length):
            code += random.choice(digits)
        return code


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, decimal.Decimal):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        elif hasattr(o, "__dict__"):
            return o.__dict__.get("name", "")
        return super(DecimalEncoder, self).default(o)


class DefaultPagination(PageNumberPagination):
    max_page_size = 1000
    page_size = 100
    page_query_param = "page"
    page_size_query_param = "page_size"

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


def render_template_to_text(message, data=dict):
    context = Context(data)
    template = Template(message)

    return template.render(context)


class CustomAPIRequestUtil(DefaultPagination, CacheUtil):
    serializer_class = None

    def __init__(self, request=None):
        self.request = request
        self.current_page = 1

    @property
    def auth_user(self):
        user = self.request.user if self.request and self.request.user else None
        if isinstance(user, AnonymousUser):
            user = None

        return user

    @property
    def auth_client(self):
        return getattr(self.auth_user, "user_client", None)

    @property
    def auth_admin(self):
        return UserTypes.admin == getattr(self.auth_user, "user_type", None)

    def report_activity(self, activity_type, data, description=None):
        if not description:
            description = str(activity_type) + " records related to " + str(data)
        print(self.auth_user, activity_type, data, description)

    def make_error(self, error: str):
        return OperationError(self.request, message=error)

    def make_400(self, error: str):
        return OperationError(
            self.request, message=error, status_code=status.HTTP_400_BAD_REQUEST
        )

    def make_404(self, error: str):
        return OperationError(
            self.request, message=error, status_code=status.HTTP_404_NOT_FOUND
        )

    def make_403(self, error: str):
        return OperationError(
            self.request, message=error, status_code=status.HTTP_403_FORBIDDEN
        )

    def make_500(self, exception):
        AppLogger.report(exception)
        return OperationError(
            self.request,
            message="Operation error: {}".format(str(exception)),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def get_request_filter_params(self, *additional_params):
        if additional_params is None:
            additional_params = []

        data = {}

        filter_bucket = self.request.query_params
        general_params = [
            "keyword",
            "search",
            "filter",
            "from_date",
            "to_date",
            "page",
            "page_size",
            "ordering",
            "is_active",
        ] + list(additional_params)

        for param in general_params:
            field_value = filter_bucket.get(param, None)
            if field_value is not None:
                if str(field_value).lower() in ["true", "false"]:
                    data[param] = str(filter_bucket.get(param))
                else:
                    data[param] = filter_bucket.get(param) or ""
            else:
                data[param] = None

        if data["filter"] and not data["keyword"]:
            data["keyword"] = data["filter"]
        if data["search"] and not data["keyword"]:
            data["keyword"] = data["search"]

        try:
            data["page"] = int(data.get("page") or 1)

        except Exception as e:
            AppLogger.report(e)
            data["page"] = 1

        try:
            data["page_size"] = int(data.get("page_size") or 100)
        except Exception as e:
            AppLogger.report(e)
            data["page_size"] = 100

        self.current_page = data.get("page")
        self.page_size = data.get("page_size")

        return data

    def get_request_filter_param_list(self, *params):
        data = {}

        filter_bucket = self.request.query_params

        for param in params:
            data[param] = filter_bucket.getlist(param, [])

        return data

    def get_paginated_list_response(self, data, count_all):
        return self.__make_pages(self.__get_pagination_data(count_all, data))

    def fetch_list(self, filter_params):
        raise Exception("Not implemented")

    def fetch_paginated_list(self, filter_params):
        queryset = self.fetch_list(filter_params=filter_params)
        page = self.paginate_queryset(queryset, request=self.request)
        data = self.serializer_class(page, many=True).data

        return self.get_paginated_list_response(data, queryset.count())

    def is_numeric(self, value):
        if value:
            try:
                numeric_value = float(value)
                return numeric_value
            except (TypeError, ValueError):
                return False
        return False

    def __get_pagination_data(self, total, data):
        prev_page_no = int(self.current_page) - 1
        last_page = ceil(total / self.page_size) if self.page_size > 0 else 0
        has_next_page = (
            total > 0
            and len(data) > 0
            and total > ((self.page_size * prev_page_no) + len(data))
        )
        has_previous_page = (prev_page_no > 0) and (
            total >= (self.page_size * prev_page_no)
        )

        return prev_page_no, data, total, last_page, has_next_page, has_previous_page

    def __make_pages(self, pagination_data):
        (
            prev_page_no,
            data,
            total,
            last_page,
            has_next_page,
            has_prev_page,
        ) = pagination_data

        prev_page_url = None
        next_page_url = None

        request_url = self.request.path

        q_list = []
        if has_next_page or has_prev_page:
            query_list = self.request.query_params or {}
            for key in query_list:
                if key != "page":
                    q_list.append(f"{key}={query_list[key]}")

        if has_next_page:
            new_list = q_list.copy()
            new_list.append("page=" + str((+self.current_page + 1)))
            q = "&".join(new_list)
            next_page_url = f"{request_url}?{q}"

        if has_prev_page:
            new_list = q_list.copy()
            new_list.append("page=" + str((+self.current_page - 1)))
            q = "&".join(new_list)
            prev_page_url = f"{request_url}?{q}"

        return {
            "page_size": self.page_size,
            "current_page": self.current_page
            if self.current_page <= last_page
            else last_page,
            "last_page": last_page,
            "total": total,
            "next_page_url": next_page_url,
            "prev_page_url": prev_page_url,
            "data": data,
        }


class MissingAPIKeyForbidden(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Auth denied. Missing required keys. API-KEY"
    default_code = "101"


class InvalidAPIKeyForbidden(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Auth denied.  Invalid API Key"
    default_code = "101"


class CustomApiRequestProcessorBase(
    CustomApiPermissionRequired, CustomAPIRequestUtil, CustomAPIResponseUtil
):
    permission_classes = [IsAuthenticated]

    payload = None
    serializer_class = None

    context: Union[dict, None] = None
    extra_context_data = dict()

    request_serializer_requires_many = False
    request_payload_requires_decryption = False

    response_payload_requires_encryption = False
    response_serializer = None
    response_serializer_requires_many = False
    wrap_response_in_data_object = False

    ref_id = None
    logging_enabled = False

    @property
    def auth_user(self):
        return self.request.user if self.request.user else None


    def process_request(self, request, target_function, **extra_args):
        self.check_required_roles_and_permissions()

        self.encrypt_response = self.response_payload_requires_encryption

        if self.request_payload_requires_decryption or settings.APP_ENC_ENABLED:
            encryption_util = AESCipher(settings.APP_ENC_KEY, settings.APP_ENC_VEC)
            request_data = encryption_util.decrypt_body(request.data)
        else:
            request_data = request.data

        if self.logging_enabled:
            self.ref_id = Util.generate_digits(18)

        if not self.context:
            self.context = dict()
        self.context["request"] = request
        if self.extra_context_data:
            for key, val in self.extra_context_data.items():
                self.context[key] = val

        try:
            if self.serializer_class and request.method in {
                "PUT",
                "POST",
                "DELETE",
                "GET",
                "PATCH",
            }:
                serializer = self.serializer_class(
                    data=request_data or dict(),
                    context=self.context,
                    many=self.request_serializer_requires_many,
                )

                if serializer.is_valid():
                    response_raw_data: Union[tuple, T] = target_function(
                        serializer.validated_data, **extra_args
                    )
                    return self.__handle_request_response(response_raw_data)
                else:
                    return self.validation_error(serializer.errors)

            elif self.serializer_class and request.method == "GET":
                # If path parameters are needed, access via `request.resolver_match.kwargs`
                path_params = (
                    request.resolver_match.kwargs
                    if hasattr(request, "resolver_match")
                    else {}
                )

                # You can combine path params with query params if necessary
                query_params = request.query_params

                # Assuming that data for GET is passed via URL params or path parameters
                serializer = self.serializer_class(
                    data={
                        **path_params,
                        **query_params,
                    },  # Merging path and query params
                    context=self.context,
                    many=self.request_serializer_requires_many,
                )

                if serializer.is_valid():
                    # Pass validated data to the target function
                    response_raw_data = target_function(
                        serializer.validated_data, **extra_args
                    )
                    return self.__handle_request_response(response_raw_data)
                else:
                    return self.validation_error(serializer.errors)

            else:
                response_raw_data: Union[tuple, T] = target_function(**extra_args)
                return self.__handle_request_response(response_raw_data)
        except Exception as e:
            AppLogger.report(e)

            response_data = {"error": str(e), "message": "Server error"}
            return self.response_with_json(
                response_data, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def __handle_request_response(self, response_raw_data):
        response_data, error_detail = None, None
        if isinstance(response_raw_data, tuple):
            response_data, error_detail = response_raw_data
        else:
            response_data = response_raw_data

        if error_detail:
            status_code = None
            if isinstance(error_detail, OperationError):
                status_code = error_detail.get_status_code()
                error_detail = error_detail.get_message()

            return self.response_with_error(error_detail, status_code=status_code)

        if self.response_serializer is not None:
            response_data = self.response_serializer(
                response_data, many=self.response_serializer_requires_many
            ).data

        if self.wrap_response_in_data_object:
            response_data = {"data": response_data}

        return self.response_with_json(response_data)


def generate_password():
    letters = "".join(
        (random.choice(string.ascii_letters) for _ in range(random.randint(10, 15)))
    )
    digits = "".join(
        (random.choice(string.digits) for _ in range(random.randint(3, 5)))
    )
    symbols = random.choice("@#$%^*-_+=")

    sample_list = list(letters + digits + symbols)
    random.shuffle(sample_list)
    return "".join(sample_list)


def generate_username(*names, suggestion: str = None, suffix: int = None):
    if not suggestion:
        names = list(names)
        if not names:
            suggestion = "".join(
                (
                    random.choice(string.ascii_lowercase)
                    for _ in range(random.randint(10, 15))
                )
            )
        else:
            suggestion = slugify("".join(names))

    if suffix:
        suggestion = f"{suggestion}{suffix}"

    from accounts.services.users import UserService

    user, _ = UserService().fetch_single_by_username(suggestion)

    if user:
        new_suffix = 1
        if suffix:
            new_suffix = str(random.randint(1, 999999))

        return generate_username(suggestion=suggestion, suffix=new_suffix)

    return suggestion


def check_tenant_from_payload_or_query_string(request):
    try:
        if request.data.get("tenant_id"):
            return request.data.get("tenant_id")
    except:
        pass

    try:
        if request.query_params.get("tenant_id"):
            return request.query_params.get("tenant_id")
    except:
        pass

    return ""


def generate_ref():
    _id = uuid4().fields

    ref = str(_id[-1]) + str(_id[-2] + _id[-3])

    return ref


def zerofy_number(number):
    return "{:02d}".format(number)


def get_unique_id(prefix=""):
    rand_no = ""
    for i in range(0, 3):
        rand_no += random.choice("0123456789")

    date_to_string = datetime.strftime(
        timezone.now(), "%Y%m%d%H%M%S"
    ) + get_random_string(4, allowed_chars="0123456789")

    return f"{prefix}{date_to_string[3:-2]}{rand_no}"


def generate_ref_id(prefix="", length=5):
    rand_no = ""
    for i in range(0, length):
        rand_no += random.choice("0123456789")

    date_to_string = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S") + rand_no

    return f"{prefix}{date_to_string}"


def make_http_request(method, url, headers=None, data=None, json=None):
    methods_dict = {
        HTTPMethods.get: requests.get,
        HTTPMethods.post: requests.post,
        HTTPMethods.patch: requests.patch,
        HTTPMethods.options: requests.options,
        HTTPMethods.delete: requests.delete,
    }

    try:
        request_method = methods_dict.get(method.upper())
        if not request_method:
            return None, f"Unsupported method: {method}"

        if json is not None:
            response = request_method(url, headers=headers, json=json)
        elif data is not None:
            response = request_method(url, headers=headers, data=data)
        else:
            response = request_method(url, headers=headers)

        # AppLogger.print("Response text", response.text)
        # print("response json: ", response.json())

        if response.ok:
            return response.json(), None

        try:
            _ = response.json()
            return None, response.text
        except:
            pass

        return None, f"Request failed with status code: {response.status_code}"
    except Exception as e:
        AppLogger.report(e)
        return None, f"Request error: {str(e)}"


def user_type_required(*user_types):
    def decorator(f):
        @wraps(f)
        def _wrapped_view(view, request, *args, **kwargs):
            if getattr(request.user, "user_type", None) not in user_types:
                return CustomAPIResponseUtil().response_with_message(
                    "Permission denied", status_code=403
                )

            return f(view, request, *args, **kwargs)

        return _wrapped_view

    return decorator



def client_type_required(*client_types):
    from accounts.models import UserTypes

    def decorator(f):
        @wraps(f)
        def _wrapped_view(view, request, *args, **kwargs):
            if getattr(request.user, "user_type", None) != UserTypes.customer:
                return CustomAPIResponseUtil().response_with_message(
                    "Permission denied", status_code=403
                )
            try:
                client = getattr(request.user, "user_client", None)
            except Exception as e:
                AppLogger.report(e)
                client = None

            if not client or client.client_type not in client_types:
                return CustomAPIResponseUtil().response_with_message(
                    "Permission denied", status_code=403
                )

            return f(view, request, *args, **kwargs)

        return _wrapped_view

    return decorator


def permission_or_client_type_required(permission, *client_types):
    from accounts.models import UserTypes
    from accounts.services.users import UserService

    def decorator(f):
        @wraps(f)
        def _wrapped_view(view, request, *args, **kwargs):

            user = request.user
            user_service = UserService(request)

            if user.user_type == UserTypes.user and permission is not None:
                if permission in user_service.get_user_permission_names(user):
                    return f(view, request, *args, **kwargs)

            client = getattr(user, "user_client", None)

            if client and client.client_type not in client_types:
                return CustomAPIResponseUtil().response_with_message(
                    "Permission denied", status_code=403
                )

            return f(view, request, *args, **kwargs)

        return _wrapped_view

    return decorator


def generate_otp():
    if settings.DEBUG:
        otp = "123456"
    else:
        otp = str(random.randint(1, 999999)).zfill(6)

    hashed_otp = make_password(otp)

    return otp, hashed_otp


def check_otp_time_expired(otp_requested_at, duration=10, use_pyotp=False):
    if not is_aware(otp_requested_at):
        otp_requested_at = make_aware(otp_requested_at)

    created_at = otp_requested_at
    current_time = timezone.now()
    time_difference = current_time - created_at
    time_difference_minutes = time_difference.seconds / 60

    return time_difference_minutes > duration


def compare_password(input_password, hashed_password):
    return check_password(input_password, hashed_password)


def is_valid_file_extension(file_extension):
    recognized_file_extension_list = [
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".csv",
        ".doc",
        ".docx",
        ".xlsx",
    ]
    return file_extension in recognized_file_extension_list


def format_phone_number(phone, region_code=None):
    if not region_code:
        region_code = "NG"
    try:
        x = phonenumbers.parse(phone, region_code)
        phone = phonenumbers.format_number(x, phonenumbers.PhoneNumberFormat.E164)

        if phonenumbers.is_valid_number_for_region(x, region_code):
            return phone
    except Exception as e:
        AppLogger.report(e)

    return None


def format_date(date_str):
    try:
        return datetime.strptime("%Y-%m-%d", date_str).strftime("%Y-%m-%d")
    except:
        try:
            return datetime.strptime("%d-%m-%Y", date_str).strftime("%Y-%m-%d")
        except:
            return datetime.strptime("%d/%m/%Y", date_str).strftime("%Y-%m-%d")


def evaluate_formular(formular, **data):
    return eval(formular, data, {})


def get_days_from_today(days=30):
    current_datetime = timezone.now()
    day = current_datetime + timedelta(days=days)

    return day


def check_date_format_valid(*dates):
    dates = [date for date in dates if date is not None]
    for date_str in dates:
        try:
            formatted_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None, "Invalid Date Format"

    return True, None


def check_year_valid(*years):
    try:
        for year in years:
            if len(year) < 4:
                return None, "Year must be a valid 4 digits"
            year = int(year)
            if 1800 >= year or year >= 9999:
                return None, "Invalid year input"
        return True, None
    except:
        return None, "Invalid year input"


def generate_unique_reference():
    """
    Generate a highly unique and random reference string.
    Combines a UUID, timestamp, and random characters.
    """
    uuid_part = str(uuid.uuid4()).replace("-", "")

    timestamp_part = str(int(time.time() * 1000))

    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    unique_reference = f"{uuid_part[:12]}{timestamp_part}{random_part}"
    return unique_reference


def send_email(
        subject: str,
        to: Union[str, list],
        message: str,
        html_template: Optional[str] = None,
        context: Optional[Dict] = None,
        from_email: Optional[str] = None
) -> bool:
    """
    Sends an email with optional HTML content.

    :param subject: Email subject
    :param to: Recipient email(s). Can be a string or a list of emails.
    :param message: Plain text message
    :param html_template: Path to the HTML template (optional)
    :param context: Context dictionary for rendering the HTML template (optional)
    :param from_email: Sender's email (optional)
    :return: True if the email is sent successfully, False otherwise
    """
    try:
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        if from_email is None:
            from_email = "no-reply@pusheat.co"
        print(f"Sending email to: {to}")
        print(f"From email: {from_email}")
        print(f"SMTP user: {settings.EMAIL_HOST_USER}")
        if isinstance(to, str):
            to = [to]

        html_content = None
        if html_template and context:
            try:
                html_content = render_to_string(template_name=html_template, context=context)

                # AppLogger.error(f"Rendered HTML content: {html_content[:50]}...")
            except Exception as render_error:
                AppLogger.error(f"Failed to render template: {str(render_error)}")
                return False
        plain_message = strip_tags(html_content)
        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=to,
        )
        if html_content:
          email_msg.attach_alternative(html_content, "text/html")

        email_msg.send()
        return True

    except Exception as e:
        AppLogger.print(f"Failed to send email to {to}: {e}")
        return False
