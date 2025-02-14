from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from accounts.models import User
from accounts.services.users import UserService
from business.models import Driver
from business.service import DriverService
from core.errors.app_errors import OperationError
from services.util import CustomAPIRequestUtil


class ClientService(CustomAPIRequestUtil):
    def __init__(self, request=None):
        super().__init__(request)

    def register_customer(self, payload, user:User):
        for field, value in payload.items():
            setattr(user, field, value)

        user.registration_complete = True
        user.save()

        return user, None

    def filter_qs_by_date(self, qs, start_date=timezone.now(), end_date=None):
        if start_date:
            start_date = timezone.datetime.strptime(str(start_date), "%Y-%m-%d")
            qs = qs.filter(created_at__gte=start_date)
        if end_date:
            end_date = timezone.datetime.strptime(str(end_date), "%Y-%m-%d")
            qs = qs.filter(created_at__lte=end_date)
        return qs


    def register_driver(self, payload, user:User) -> (Driver, OperationError): # type: ignore
        driver_service = DriverService(self.request)
        if not user:
            return None, "User not found"
        payload["email"] = user.email
        user.phone_number = payload.get("phone_number")
        user.save(update_fields=["phone_number"])
        return driver_service.create(payload.copy(), user)

    def update_driver(self, payload, id=None, user=None) -> (Driver, OperationError): # type: ignore
        driver_service = DriverService(self.request)
        if not user:
            driver, error = driver_service.fetch_single(id)
            if error:
                return None, error

        user = driver.user
        if user:
            user_service = UserService(self.request)
            user_service.update_user(
                {
                    "full_name": payload.get("full_name"),
                    "email": payload.get("email") or user.email,
                    "role_ids": [],
                },
                user=user,
            )

        driver, error = driver_service.update(payload, driver=driver)

        if error:
            return None, error

        return driver, None

class PasswordService(CustomAPIRequestUtil):
    def __init__(self, request):
        super().__init__(request)

    def verify_password(self, incoming_password, db_password):
        return check_password(incoming_password, db_password)

    def update_password(self, payload, user:User):
        new_password = payload.get("new_password")
        old_password = payload.get("old_password")

        # Verify old password
        user_password = user.password

        is_verified = self.verify_password(old_password, user_password)

        if not is_verified:
            return None, "Password Incorrect"

        user.password = make_password(new_password)
        user.save()

        return "Password set successfully", None
