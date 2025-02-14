import random
import string
from typing import Any, List, Optional, Tuple

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.constants.roles_permissions import RoleEnum
from accounts.models import Permission, Role, User, UserTypes
from accounts.serializers.users import UserListSerializer
from accounts.services.roles_permissions import RoleService
from core.errors.app_errors import OperationError
from crm.constants import ActivityType
from services.log import AppLogger
from services.util import CustomAPIRequestUtil, generate_password


class UserService(CustomAPIRequestUtil):
    def gen_cache_key(
        self, key_type: str, user: Optional[User] = None, user_id: Optional[int] = None
    ) -> str:
        if user:
            if key_type == "permission_names":
                return self.generate_cache_key("user", user.id, "perms", "names")
            if key_type == "role_names":
                return self.generate_cache_key("user", user.id, "roles", "names")
        if user_id:
            if key_type == "user_id":
                return self.generate_cache_key("user_id", user_id)
            if key_type == "user_email":
                return self.generate_cache_key("user_email", user_id)
            if key_type == "user_username":
                return self.generate_cache_key("user_username", user_id)
        return ""

    def get_user_permission_names(self, user: User) -> List[str]:
        def __do_get_permission_names() -> Tuple[List[str], None]:
            if (
                user.is_superuser
                or user.roles.filter(name__exact=RoleEnum.sysadmin).exists()
            ):
                permissions = Permission.objects.values_list("name", flat=True)
            else:
                permissions = (
                    Permission.objects.order_by("name")
                    .filter(
                        role__permissions__id__in=user.roles.values_list(
                            "pk", flat=True
                        )
                    )
                    .distinct()
                    .values_list("name", flat=True)
                )
            return list(permissions), None

        perms, error = self.get_cache_value_or_default(
            self.gen_cache_key("permission_names", user=user), __do_get_permission_names
        )
        return perms if not error else []

    def get_user_role_names(self, user: User) -> List[str]:
        def __do_get_role_names() -> Tuple[List[str], None]:
            roles = user.roles.values_list("name", flat=True)
            return list(roles), None

        perms, error = self.get_cache_value_or_default(
            self.gen_cache_key("role_names", user=user), __do_get_role_names
        )
        return perms if not error else []

    @classmethod
    def is_super_user(cls, user: User) -> bool:
        return user.is_superuser

    def delete(
        self, username: Optional[str] = None, user: Optional[User] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        if not user:
            user, error = self.fetch_single_by_username(username)
            if error:
                return None, error

        if user.id == self.auth_user.id:
            return None, "Invalid operation."

        user.deleted_at = timezone.now()
        user.deleted_by = self.auth_user
        user.save()

        self.clear_temp_cache(user)
        self.report_activity(ActivityType.delete, user)

        return user, None

    def hard_delete(self, user: User) -> Tuple[Optional[User], None]:
        user.delete()
        self.clear_temp_cache(user)
        self.report_activity(ActivityType.delete, user)
        return user, None

    def create_user(self, payload: dict) -> Tuple[Optional[User], Optional[str]]:
        from accounts.tasks import send_default_password_queue

        username = payload.get("username")
        email = payload.get("email")
        is_verified = payload.get("is_verified", False)
        full_name = payload.get("full_name")
        device_id = payload.get("device_id", None)
        device_name = payload.get("device_name")

        if self.user_exists_by_username_or_email(
            email=email,
            username=username,
        ):
            return (
                None,
                "User with provided username, email or phone number already exists",
            )

        password = payload.get("password")
        send_password_email = False
        generated_password = None

        if not password:
            generated_password = generate_password()
            password = make_password(generated_password)
            send_password_email = True

        try:
            with transaction.atomic():
                user = User.objects.create(
                    username=username,
                    email=email,
                    password=password,
                    is_verified=is_verified,
                    full_name=full_name,
                )

                if device_id and device_name:
                    user.devices.append({"device_id": device_id, "device_name": device_name})

                role_ids = payload.get("role_ids", [])
                if role_ids:
                    role_service = RoleService(self.request)
                    roles = role_service.fetch_by_ids(role_ids)
                    user.roles.add(*roles)

                self.clear_temp_cache(user)
                self.report_activity(ActivityType.create, user)
                user.save()

                # Fetch the updated user for returning
                user, error = self.fetch_single_by_username(user.username)

                if send_password_email and generated_password:
                    send_default_password_queue.delay(email, generated_password)

                return user, error
        except Exception as e:
            # Handle the error as needed (e.g., logging)
            return None, str(e)

    def update_user(
        self, payload: dict, username: Optional[str] = None, user: Optional[User] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        if not user:
            user, error = self.fetch_single_by_username(username)
            if user is None or error:
                return None, error or "User does not exist"

        email = payload.get("email")
        phone_number = payload.get("phone_number")
        dob = payload.get("dob")
        username = payload.get("username")
        gender = payload.get("gender")
        user_type = payload.get("user_type")
        registration_complete = payload.get("registration_complete")
        fcm_token = payload.get("fcm_token")
        update_kyc_required = payload.get("update_kyc_required")

        if (
            email
            and (user_with_email := self.find_user_by_email(email)[0])
            and user_with_email != user
        ):
            return None, "Email already exists!"

        if (
            phone_number
            and (user_with_phone := self.find_user_by_phone_number(phone_number)[0])
            and user_with_phone != user
        ):
            return None, "Phone number already exists!"

        user.full_name = payload.get("full_name", user.full_name)
        user.email = email or user.email
        user.phone_number = phone_number or user.phone_number
        user.username = username or user.username
        user.gender = gender or user.gender
        user.dob = dob or user.dob
        user.registration_complete = registration_complete or user.registration_complete
        user.user_type = user_type or user.user_type
        user.updated_at = timezone.now()
        user.updated_by = user
        user.fcm_token = fcm_token or user.fcm_token
        user.update_kyc_required = update_kyc_required or user.update_kyc_required
        user.save(
            update_fields=[
                "username",
                "full_name",
                "phone_number",
                "gender",
                "user_type",
                "dob",
                "registration_complete",
                "updated_at",
                "updated_by",
                "fcm_token",
            ]
        )

        if role_ids := payload.get("role_ids"):
            role_service = RoleService(self.request)
            roles = role_service.fetch_by_ids(role_ids)
            user.roles.set(roles)

        self.clear_temp_cache(user)
        self.report_activity(ActivityType.update, user)
        user.save()

        user, error = self.fetch_single_by_username(user.username)
        return user, error

    def fetch_single_by_username(
        self, username: str
    ) -> Tuple[Optional[User], Optional[str]]:
        def __fetch() -> Tuple[Optional[User], Optional[str]]:
            user = (
                User.objects.prefetch_related("roles")
                .filter(username__iexact=username)
                .first()
            )
            return user, None if user else f"User '{username}' not found"

        cache_key = self.gen_cache_key("user_username", user_id=username.lower())
        return self.get_cache_value_or_default(cache_key, __fetch)

    def find_user_by_email(self, email: str) -> Tuple[Optional[User], Optional[str]]:
        def __fetch() -> Tuple[Optional[User], Optional[str]]:
            user = (
                User.objects.prefetch_related("roles")
                .filter(email__iexact=email)
                .first()
            )
            return user, None if user else f"User with email '{email}' not found"

        cache_key = self.gen_cache_key("user_email", user_id=email.lower())
        return self.get_cache_value_or_default(cache_key, __fetch)

    @classmethod
    def find_user_by_phone_number(
        cls, phone_number: str
    ) -> Tuple[Optional[User], Optional[str]]:
        user = User.objects.filter(phone_number__iexact=phone_number).first()
        return (
            user,
            None if user else f"User with phone number '{phone_number}' not found",
        )

    @classmethod
    def user_exists_by_username_or_email(
        cls,
        email: Optional[str] = None,
        username: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> bool:
        if not email and not username:
            return False

        query = Q()
        if username:
            query |= Q(username__iexact=username)
        if email:
            query |= Q(email__iexact=email)
        if phone_number:
            query |= Q(phone_number__iexact=phone_number)

        return User.objects.filter(query).exists()

    def activate_or_deactivate(
        self, payload: dict, username: Optional[str] = None, user: Optional[User] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        if not user:
            user, error = self.fetch_single_by_username(username)
            if error:
                return None, error

        is_activate = payload.get("is_active")
        reason = payload.get("reason", "")
        message = None

        if is_activate and user.deactivated_at is not None:
            user.deactivated_at = None
            user.deactivated_by = None
            message = f"{user.username} account activated successfully."
        elif not is_activate and user.deactivated_at is None:
            user.deactivated_at = timezone.now()
            user.deactivated_by = self.auth_user
            user.deactivation_reason = reason
            message = f"{user.username} account deactivated successfully."
        else:
            return (
                None,
                f"Invalid operation, user is already {'active' if is_activate else 'deactivated'}",
            )

        user.save()
        self.clear_temp_cache(user)
        self.report_activity(
            ActivityType.deactivate if not is_activate else ActivityType.activate, user
        )
        return message, None

    @classmethod
    def find_user_by_otp(cls, otp):
        try:
            user = User.available_objects.prefetch_related("roles").get(otp_base32=otp)
            return user, None
        except User.DoesNotExist:
            return None, f"User not found"
        except Exception as e:
            AppLogger.report(e)
            return None, str(e)

    def fetch_list(self, filter_params) -> (Any, OperationError):
        filter_user_type = filter_params.get("user_type")
        filter_keyword = filter_params.get("keyword")
        self.page_size = filter_params.get("page_size", 100)

        q = Q()
        if filter_keyword:
            q &= (
                Q(username__icontains=filter_keyword)
                | Q(full_name__icontains=filter_keyword)
                | Q(phone_number__icontains=filter_keyword)
                | Q(email__icontains=filter_keyword)
            )

        if not filter_user_type:
            filter_user_type = UserTypes.customer

        if filter_user_type:
            q &= Q(user_type__iexact=filter_user_type)

        queryset = (
            User.available_objects.filter(q)
            .exclude(pk=self.auth_user.pk)
            .prefetch_related("roles")
            .order_by("-created_at")
        )
        page = self.paginate_queryset(queryset, request=self.request)
        data = UserListSerializer(page, many=True).data

        return self.get_paginated_list_response(data, queryset.count())

    def clear_temp_cache(self, user):
        self.clear_cache(self.gen_cache_key("permission_names", user_id=user))
        self.clear_cache(self.gen_cache_key("role_names", user_id=user))
        self.clear_cache(self.gen_cache_key("user_id", user_id=user.id))
        self.clear_cache(
            self.gen_cache_key("user_username", user_id=user.username.lower())
        )
        self.clear_cache(self.gen_cache_key("user_email", user_id=user.email.lower()))

    @classmethod
    def fetch_fcm_tokens(cls, user_ids):
        return list(
            User.available_objects.filter(pk__in=user_ids, fcm_token__isnull=False)
            .distinct()
            .values_list("fcm_token", flat=True)
        )

    def check_username(self, payload):
        username = payload.get("username")
        count = payload.get("count", 4)
        suggestions = []

        user_exists = User.objects.filter(username=username).exists()
        if user_exists:
            suggestions = self.generate_suggestions(username, count=count)


        response = {
            'available': not user_exists,
            'message': 'Username is available.' if not user_exists else 'Username already taken.',
            'suggestions': suggestions
        }

        return response, None

    def generate_suggestions(self, username, count=4):
        suggestions = set()
        username_lower = username.lower()
        patterns = [
            lambda u: f"{u}{random.randint(1, 999)}",
            lambda u: f"{u}_{random.choice(string.ascii_lowercase)}",
            lambda u: f"{u}{random.choice(['123', 'xyz', 'abc'])}",
            lambda u: f"{u}_{random.randint(100, 999)}",
            lambda u: f"{u}_{u[::-1][:3]}",
            lambda u: f"{username_lower}_{random.choice(['x', 'z', 'q'])}{random.randint(1, 9)}",
            lambda u: f"{u}_{random.randint(1900, 2023)}"

        ]

        while len(suggestions) < count:
            pattern = random.choice(patterns)
            suggestion = pattern(username)
            if not User.objects.filter(username=suggestion).exists():
                suggestions.add(suggestion)

        return list(suggestions)
