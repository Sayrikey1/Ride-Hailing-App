from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from email_validator import validate_email

from accounts.models import User
from services.log import AppLogger


class EmailOrUsernameModelBackend(ModelBackend):
    """
    This is a ModelBacked that allows authentication
    with either a username or an email address.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):

        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        if username is None or password is None:
            return

        try:
            email_info = validate_email(username, check_deliverability=False)
            fields = {"email__iexact": email_info.normalized}
        except Exception:
            fields = {"username__iexact": username}

        try:
            user = get_user_model().objects.get(**fields)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except User.DoesNotExist:
            pass
        except Exception as e:
            AppLogger.report(e)
        return None
