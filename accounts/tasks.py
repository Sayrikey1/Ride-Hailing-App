from datetime import timedelta, timezone

from celery import app
from django.conf import settings

from accounts.services.users import UserService
from services.log import AppLogger
from services.util import send_email


def get_user_data(email):
    user_service = UserService(None)
    user, error = user_service.find_user_by_email(email)

    if error:
        AppLogger.log(f"{error}")
        return None, error

    name = user.get_full_name()

    data = {"name": name or "User"}

    return data, None


@app.shared_task
def send_activation_otp_email_queue(email, otp, name=None):
    if not email:
        AppLogger.print("Invalid email passed to send_activation_otp_email_queue")
        return

    AppLogger.print("Sending activation OTP to", email)


    # Get user data if name not provided
    if not name:
        data, error = get_user_data(email)
        if not error:
            name = data.get("name")


    subject = "Your Activation OTP Code"
    message = f"Your OTP code is: {otp}"
    html_template = 'emails/auth/activation.html'
    context = {'otp': otp, 'email': email,  "name": name or "User"}

    AppLogger.print("Sending activation otp to", email)
    success = send_email(subject, email, message=message, html_template=html_template, context=context)
    if success:
        AppLogger.print(f"Activation OTP sent successfully to {email}")
    else:
        AppLogger.print(f"Failed to send activation OTP to {email}")

    # util = NotificationUtil()
    # util.send_notification_from_template(
    #     emails=[email],
    #     message_type=MessageTypes.account_activation,
    #     data={
    #         "name": name or "User",
    #         "otp": otp,
    #         "email": email,
    #         "app_url": settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else '#',
    #         "support_email": settings.SUPPORT_EMAIL if hasattr(settings, 'SUPPORT_EMAIL') else settings.DEFAULT_FROM_EMAIL,
    #     },
    # )


@app.shared_task
def send_reset_password_otp_queue(email, otp):
    if not email:
        AppLogger.print("Invalid email passed to send_reset_password_otp_queue")
        return

    AppLogger.print("Sending reset password OTP to", email)

    data, error = get_user_data(email)
    util = NotificationUtil()

    if error:
        name = "User"
    else:
        name = data.get("name", "User")

    subject = "Reset Your Password OTP Code"
    message = f"Your OTP code for password reset is: {otp}"
    html_template = 'emails/auth/password_reset.html'
    context = {'otp': otp, 'email': email, "name": name or "User"}

    AppLogger.print("Sending password reset OTP to", email)
    success = send_email(subject, email, message=message, html_template=html_template, context=context)

    if success:
        AppLogger.print(f"Password reset OTP sent successfully to {email}")
    else:
        AppLogger.print(f"Failed to send password reset OTP to {email}")

    # util.send_notification_from_template(
    #     emails=[email],
    #     message_type=MessageTypes.password_reset,
    #     data={
    #         "name": name,
    #         "otp": otp,
    #         "email": email,
    #         "support_email": settings.SUPPORT_EMAIL if hasattr(settings, 'SUPPORT_EMAIL') else settings.DEFAULT_FROM_EMAIL,
    #     },
    # )


@app.shared_task
def send_default_password_queue(email, password):
    if not email:
        AppLogger.print(
            "Invalid email passed to send_default_password_queue for default password"
        )
        return

    AppLogger.print("Sending default password to", email)

    data, error = get_user_data(email)
    util = NotificationUtil()

    if error:
        return

    util.send_notification_from_template(
        emails=[email],
        message_type=MessageTypes.default_password,
        data={"name": data.get("name"), "password": password},
    )
