from disposable_email_checker.validators import validate_disposable_email
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.utils.translation import gettext as translate
from email_validator import validate_email
from password_validator import PasswordValidator
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.services.users import UserService
from services.cache_util import CacheUtil
from services.log import AppLogger
from services.util import format_phone_number, render_template_to_text


class UserPasswordResetSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(max_length=250, min_length=12)
    new_password = serializers.CharField(max_length=250, min_length=12)


class LoginSerializer(TokenObtainSerializer):
    fcm_token = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    username = serializers.CharField()
    password = serializers.CharField()
    device_id = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    device_name = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    token_class = RefreshToken

    def validate(self, attrs):
        username = attrs.get("username").lower()
        password = attrs.get("password")

        authenticate_kwargs = {"username": username, "password": password}

        cache_util = CacheUtil()
        login_count_cache_key = cache_util.generate_cache_key("login_count", username)

        login_count, error = cache_util.get_cache_value_or_default(
            cache_key=login_count_cache_key
        )

        if login_count and login_count >= 10:
            raise serializers.ValidationError(
                translate("auth.login.account_deactivated.too.many.tries"), "username"
            )

        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        try:
            self.user = authenticate(**authenticate_kwargs)
        except User.MultipleObjectsReturned:
            raise serializers.ValidationError(
                translate("auth.login.mistaken_identity"), "username"
            )

        except Exception as e:
            AppLogger.report(e)
            raise serializers.ValidationError(
                render_template_to_text(translate("auth.login.error"), {"error": str(e)}),
                "username",
            )

        if self.user is None:
            login_count = 1 if login_count is None else login_count + 1
            cache_util.set_cache_value(login_count_cache_key, login_count, timeout=1200)

            if login_count > 5 and not settings.DEBUG:
                raise serializers.ValidationError(
                    {"username": translate("auth.login.access_denied")}
                )
            raise serializers.ValidationError(
                # {"username": translate("auth.login.access_denied")}
                {"username": "Invalid Credentials"}
            )
        if self.user.deleted_at:
            raise serializers.ValidationError(translate("auth.login.error"), "username")

        if self.user.deactivated_at:
            raise serializers.ValidationError(
                translate("auth.login.account_deactivated"), "username"
            )

        if not self.user.registration_complete:
            raise serializers.ValidationError("Registration is not yet complete")

        authentication = self.get_token(self.user)
        return {
            "user": self.user,
            "access_token": str(authentication.access_token),
            "refresh_token": str(authentication),
            "fcm_token": attrs.get("fcm_token"),
        }


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    full_name = serializers.CharField(required=True)
    device_id = serializers.CharField(required=True, allow_null=True, allow_blank=True)
    device_name = serializers.CharField(required=True, allow_null=True, allow_blank=True)

    def validate(self, attrs):
        data = attrs.copy()

        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password", "")

        password_schema = PasswordValidator()
        password_schema.min(8).uppercase().lowercase().digits().symbols()

        if not password_schema.validate(password):
            raise serializers.ValidationError(
                # translate("auth.register.password_insecure"), "password"
                "Your password should contain at least 8 characters, an uppercase, a lowercase, a digit and symbol ", "password"
            )

        try:
            email_info = validate_email(email, check_deliverability=True)
            email = email_info.normalized

            # Check for disposable email providers like "mailinator.com"
            if not settings.DEBUG:
                validate_disposable_email(email)

        except Exception as e:
            raise serializers.ValidationError("Invalid email provided", "email")

        if User.objects.filter(Q(email__iexact=email)).exists():
            # raise serializers.ValidationError(translate("auth.register.email_exists"), "email")
            raise serializers.ValidationError("An account with the provided email already exists", "email")

        data["email"] = email
        data["password"] = make_password(password)

        return data


class VerifyOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()


class ResendOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OTPSerializer(serializers.Serializer):
    otp = serializers.CharField()
    email = serializers.EmailField()
    fcm_token = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class VerifyAuthenticatorOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()
    fcm_token = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class UserOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "otp_enabled",
            "otp_verified",
            "otp_base32",
            "otp_auth_url",
        ]

class DriverRegistrationSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    username = serializers.CharField()
    gender = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    fcm_token = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    dob = serializers.DateField()
    email = serializers.EmailField()
    address = serializers.CharField(required=False)
    license_number = serializers.CharField()

    def validate(self, attrs):
        data = attrs.copy()
        phone_number = format_phone_number(data.get("phone_number"))
        if not phone_number:
            raise serializers.ValidationError(
                translate("auth.register.phone_number_invalid"), "phone_number"
            )

        data["phone_number"] = phone_number
        return data

class CustomerRegistrationSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    username = serializers.CharField()
    gender = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    fcm_token = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    dob = serializers.DateField()
    email = serializers.EmailField()
    address = serializers.CharField(required=False)

    def validate(self, attrs):
        data = attrs.copy()
        phone_number = format_phone_number(data.get("phone_number"))
        if not phone_number:
            raise serializers.ValidationError(
                translate("auth.register.phone_number_invalid"), "phone_number"
            )

        data["phone_number"] = phone_number
        return data


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordRequestSerializer(serializers.Serializer):
    password = serializers.CharField()
    email = serializers.EmailField()
    otp = serializers.CharField()

    def validate(self, attrs):
        data = attrs.copy()

        password = attrs.get("password", "")
        email = attrs.get("email")

        password_schema = PasswordValidator()
        password_schema.min(8).uppercase().lowercase().digits().symbols()

        if not password_schema.validate(password):
            raise serializers.ValidationError(
                translate("auth.register.password_insecure"), "password"
            )

        user_service = UserService(None)
        user, error = user_service.find_user_by_email(email)

        data["password"] = password
        data["user"] = user

        return data

class ResetPasswordInAppRequestSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()
    email = serializers.EmailField()

    def validate(self, attrs):
        data = attrs.copy()

        current_password = attrs.get("current_password", "")
        new_password = attrs.get("new_password", "")
        email = attrs.get("email")

        password_schema = PasswordValidator()
        password_schema.min(8).uppercase().lowercase().digits().symbols()

        if not password_schema.validate(new_password):
            raise serializers.ValidationError(
                translate("auth.register.password_insecure"), "password"
            )

        user_service = UserService(None)
        user, error = user_service.find_user_by_email(email)

        data["current_password"] = current_password
        data["new_password"] = new_password
        data["user"] = user

        return data

