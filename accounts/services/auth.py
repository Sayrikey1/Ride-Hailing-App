
import pyotp
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import (PasswordResetRequest,
                             PasswordResetRequestStatus, RegisterLog, User,
                             UserTypes)
from accounts.services.users import UserService
from accounts.tasks import (send_activation_otp_email_queue,
                            send_reset_password_otp_queue)
from crm.services.clients import ClientService
# from payment.services import WalletService
from services.log import AppLogger
from services.util import (CustomAPIRequestUtil, check_otp_time_expired,
                           compare_password, generate_otp, generate_username)


class AuthService(CustomAPIRequestUtil):
    def login(self, payload) -> dict:
        user : User = payload.get("user")
        fcm_token = payload.get("fcm_token")

        access_token = str(payload.get("access_token"))
        refresh_token = str(payload.get("refresh_token"))

        username = user.username
        user_service = UserService(self.request)

        permissions = user_service.get_user_permission_names(user)
        roles = user_service.get_user_role_names(user)

        user_type = user.user_type or UserTypes.customer

        response_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "username": username,
            "full_name": user.full_name,
            "roles": roles,
            "permissions": permissions,
            "user_type": user_type,
        }

        if user_type == UserTypes.driver:
            response_data["update_kyc_required"] = user.update_kyc_required

        self.update_last_login(user, fcm_token)
        return response_data

    def request_password_reset(self, payload):
        try:
            # message = {"message": _("auth.reset_password.sent")}
            message = {"message": "Your reset password OTP has been sent successfully."}
            email = payload.get("email")

            auth_service = UserService(self.request)
            user, error = auth_service.find_user_by_email(email)

            if user is None or error:
                AppLogger.report(error)
                return message, None

            otp, hashed_otp = generate_otp()

            if not hasattr(user, "password_reset_request"):
                self.create_password_reset_request(user)

            password_reset_request = user.password_reset_request

            password_reset_request.otp = hashed_otp
            password_reset_request.status = PasswordResetRequestStatus.available
            password_reset_request.updated_at = timezone.now()

            password_reset_request.save(update_fields=["otp", "status", "updated_at"])

            # Send email
            self.send_reset_password_link_email(email, otp)

            return message, None

        except Exception as e:
            return None, self.make_500(e)

    @classmethod
    def create_password_reset_request(cls, user):
        return PasswordResetRequest.objects.create(user=user)

    def reset_password(self, payload):
        try:
            password = payload.get("password")
            user:User = payload.get("user")
            otp = payload.get("otp")

            if user:
                password_reset_request = getattr(user, "password_reset_request", None)

                if password_reset_request:
                    if not compare_password(otp, password_reset_request.otp):
                        return {"message": _("invalid.otp")}

                    if (
                        password_reset_request.status
                        != PasswordResetRequestStatus.available
                        or check_otp_time_expired(password_reset_request.updated_at)
                    ):
                        password_reset_request.status = (
                            PasswordResetRequestStatus.expired
                        )
                        password_reset_request.save(update_fields=["status"])
                        return {"message": _("expired.otp")}

                    user.set_password(password)
                    user.save()
                    password_reset_request.status = PasswordResetRequestStatus.expired
                    password_reset_request.save(update_fields=["status"])

            return {"message": _("auth.reset_password.successful")}, None

        except Exception as e:
            return None, self.make_500(e)
    
    def reset_password_in_app(self, payload):
        try:
            user: User = payload.get("user")
            current_password = payload.get("current_password")
            new_password = payload.get("new_password")
    
            # Validate input
            if not user:
                return {"error": "User not provided."}, None
    
            if not current_password:
                return {"error": "Current password not provided."}, None
    
            if not new_password:
                return {"error": "New password not provided."}, None
    
            # Verify that the provided current password is correct.
            if not user.check_password(current_password):
                return {"error": "Wrong current password provided."}, None
    
            # Prevent using the same password.
            if user.check_password(new_password):
                return {"error": "Password is duplicate of the old one."}, None
    
            # Update and persist the new password.
            user.set_password(new_password)
            user.save()
            return {"message": "Password updated successfully."}, None

        except Exception as e:
            # Log the exception as needed before returning.
            return None, self.make_500(e)

    @classmethod
    def send_activation_otp(cls, email, otp, full_name=None):
        _ = send_activation_otp_email_queue.delay(email=email, otp=otp, name=full_name)

        return True

    def __check_existing_log(self, email):
        def do_fetch():
            log, error = None, None
            try:
                log = RegisterLog.objects.filter(Q(email__iexact=email)).first()
            except Exception as e:
                error = self.make_500(e)

            return log, error

        cache_key = self.generate_cache_key("log", "email", email)
        return self.get_cache_value_or_default(cache_key, do_fetch)

    def __create_log(self, email, payload):
        def do_create():
            log, error = None, None
            full_name = payload.get("full_name", "")
            try:
                otp, hashed_otp = generate_otp()

                log = RegisterLog.objects.create(
                    email=email,
                    payload=payload,
                    otp=hashed_otp,
                    otp_requested_at=timezone.now(),
                )
                log.save()

                self.send_activation_otp(email, otp, full_name)

            except Exception as e:
                error = self.make_500(e)

            return log, error

        cache_key = self.generate_cache_key("log", "email", email)
        return self.get_cache_value_or_default(cache_key, do_create)

    def __update_log(self, log, **kwargs):
        def do_update():
            error = None
            try:
                for field, value in kwargs.items():
                    setattr(log, field, value)

                log.save()

            except Exception as e:
                error = self.make_500(e)

            return log, error

        cache_key = self.generate_cache_key("log", "email", log.email)

        return self.get_cache_value_or_default(
            cache_key, do_update, require_fresh_data=True
        )

    def log_register(self, payload):
        email = payload.get("email")
        full_name = payload.get("full_name")
        response_data = {
            # "message": render_template_to_text(
            #     _("auth.register.otp_sent"), {"email": email}
            # )
            "message": "An OTP has been sent to your mail"
        }
        try:
            # Check existing log
            log, error = self.__check_existing_log(email=email)

            if log:
                response_data["data"] = {"email": log.email}
                if not full_name:
                    full_name = log.payload["full_name"]

                if not log.is_verified:
                    self.__resend_activation_otp(log, email, full_name)

                    # message = render_template_to_text(
                    #     _("auth.register.ongoing.otp_sent"), {"email": email}
                    # )
                    message = f"An OTP has already been sent. Please check your messages."
                    response_data["message"] = message

                    return response_data, None

                # message = render_template_to_text(
                #     _("auth.register.ongoing"), {"email": email}
                # )
                message = "Registration already begun with this account"
                response_data["message"] = message

                return response_data, None

            log, error = self.__create_log(email=email, payload=payload)

            response_data["data"] = {"email": log.email}

            return response_data, None

        except Exception as e:
            return None, self.make_500(e)

    def __resend_activation_otp(self, log, email, full_name=None):
        response_data = {
            # "message": render_template_to_text(
            #     _("auth.register.otp_just_sent"), {"email": email}
            # ),
            "message": "An OTP has been sent to your mail",
            "data": {"email": email},
        }

        if not log:
            return None, self.make_error("Invalid Account Signup")
        if not full_name:

            full_name = log.payload["full_name"]


        try:
            otp_expired = check_otp_time_expired(log.otp_requested_at, 1)

            if not otp_expired:
                return response_data, None

            # Resend Activation OTP
            otp, hashed_otp = generate_otp()

            self.send_activation_otp(email, otp, full_name)
            self.__update_log(log, otp=hashed_otp, otp_requested_at=timezone.now())

            return response_data, None

        except Exception as e:
            return None, self.make_500(e)

    def verify_register_otp(self, payload):
        email = payload.get("email")
        otp = payload.get("otp")

        try:
            log, error = self.__check_existing_log(email=email)

            if error:
                return None, self.make_error("Operation error: {}".format(error))

            if not log:
                return None, self.make_404("Account details not found, Register first!")
            # Check OTP is valid
            otp_valid = compare_password(otp, log.otp)
            if not otp_valid:
                # return None, self.make_error(_("invalid.otp"))
                return None, self.make_error("Invalid OTP provided")

            # Check OTP time
            otp_expired = check_otp_time_expired(otp_requested_at=log.otp_requested_at)
            if otp_expired:
                # return None, self.make_error(_("expired.otp"))
                return None, self.make_error("Provided OTP has expired, please request for new OTP")

            log, error = self.__update_log(
                log, is_verified=True, otp_verified_at=timezone.now()
            )

            # Create user
            account_payload = log.payload

            user_service = UserService(self.request)
            account_payload["username"] = generate_username(log.email.split("@")[0])
            account_payload["is_verified"] = True
            user, error = user_service.create_user(
                payload=account_payload,
            )
            #
            if error:
                return None, error

            response_data = {
                # "message": render_template_to_text(_("otp.verified.successfully")),
                "message": "OTP verified Successfully",
                "email": email,
            }
            return response_data, None

        except Exception as e:
            return None, self.make_500(e)

    def resend_registration_otp(self, payload):
        email = payload.get("email")

        log, error = self.__check_existing_log(email)

        if error:
            return None, self.make_error("Operation error: {}".format(error))

        response, error = self.__resend_activation_otp(log, email)

        return response, error

    def register(self, payload, register_type):
        try:
            email = payload.get("email")
            username = payload.get("username")
            user_service = UserService(self.request)
            user, user_error = user_service.find_user_by_email(email)
            if user_error:
                return None, self.make_error(user_error)

            if user.registration_complete:
                return None, self.make_error("Registration already complete")

            if not username:
                username = user.username

            client_service = ClientService(self.request)
            customer, driver, client_error = None, None, None
            payload["user_type"] = register_type
            if register_type == UserTypes.customer:
                customer, client_error = client_service.register_customer(payload, user=user)
            if register_type == UserTypes.driver:
                driver, client_error = client_service.register_driver(payload, user=user)

            if client_error:
                return None, client_error

            if not customer and not driver:
                return None, self.make_error(
                    "Unable to complete, not enough data to proceed!"
                )
            payload["registration_complete"] = True
            payload["update_kyc_required"] = register_type == UserTypes.driver
            user, error = user_service.update_user(payload, username, user)

            if error:
                # todo: use transaction save points and rollbacks instead of hard_delete
                user_service.hard_delete(user)
                return None, error
            # wallet_service = WalletService(self.request)
            # wallet_service.get_wallet(user)

            return {
                "message": _("auth.register.successful"),
                "fcm_token": user.fcm_token
                }, None
        except Exception as e:
            AppLogger.report(e)
            return None, self.make_error(str(e))

    @staticmethod
    def gen_auth_url_and_base_32_str_for_user_email(email):
        otp_base32 = pyotp.random_base32()
        otp_auth_url = pyotp.totp.TOTP(otp_base32).provisioning_uri(
            name=email.lower(), issuer_name=settings.FRONTEND_URL
        )

        return otp_auth_url, otp_base32

    @classmethod
    def verify_otp(cls, activation_key, otp):
        return pyotp.TOTP(activation_key, interval=300, digits=6).verify(otp)

    @classmethod
    def do_generate_email_otp(cls, minutes=None):
        if not minutes:
            minutes = 5
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret, interval=int(minutes * 60), digits=6)
        return secret, totp.now()

    @classmethod
    def update_last_login(cls, user, fcm_token=None):
        user.last_login = timezone.now()
        user.fcm_token = fcm_token

        user.save(update_fields=["last_login", "fcm_token"])

        if fcm_token:
            User.objects.exclude(fcm_token=fcm_token).exclude(pk=user.pk).update(
                fcm_token=None
            )

    def validate_authenticator_otp(self, payload):
        pass


    @classmethod
    def send_reset_password_link_email(cls, email, otp):
        _ = send_reset_password_otp_queue.delay(email=email, otp=otp)

        return True


class TokenService(CustomAPIRequestUtil):
    @classmethod
    def create_access_token(cls, user, expiry=None):
        token = RefreshToken.for_user(user)

        if expiry is not None:
            token.set_exp(f"{expiry}")

        return str(token), str(token.access_token)
