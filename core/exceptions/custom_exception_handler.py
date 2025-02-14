from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

from services.encryption_util import AESCipher


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if response.status_code not in [200, 201] and "detail" in response.data:
            if (
                "code" in response.data
                and response.data.get("code") == "user_not_found"
            ):
                message = _("request.authorization.failed")
            else:
                message = response.data["detail"]

            data = {"message": message}

            if settings.APP_ENC_ENABLED:
                cipher = AESCipher(settings.APP_ENC_KEY, settings.APP_ENC_VEC)
                data = cipher.encrypt_nested(data)
            response.data = data

    return response


class RateLimitException(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = _("too.many.request")
