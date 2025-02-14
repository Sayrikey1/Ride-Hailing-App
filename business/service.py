from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Q
from django.utils import timezone

from business.models import Driver
from core.errors.app_errors import OperationError
from crm.constants import ActivityType
from services.util import CustomAPIRequestUtil


class DriverService(CustomAPIRequestUtil):
    def __init__(self, request):
        super().__init__(request)

    def create(self, payload, user):
        try:
            if not user:
                return None, "Invalid user"

            driver = Driver.objects.create(
                user=user,
                license_number=payload.get("license_number"),
                rating=payload.get("rating", 0),
                vehicle=payload.get("vehicle"),
            )
            return driver, None

        except ValidationError as e:
            return None, self.make_error(f"Validation error: {e}")

        except TypeError as e:
            return None, self.make_error(f"Type error: {e}")

        except Exception as e:
            return None, self.make_error(f"Unexpected error: {e}")

    def update(self, payload, driver):
        try:
            if not driver:
                return None, "Driver instance is invalid"

            for key, value in payload.items():
                if hasattr(driver, key):
                    setattr(driver, key, value)

            driver.save()
            return driver, None

        except ValidationError as e:
            return None, self.make_error(f"Validation error: {e}")

        except TypeError as e:
            return None, self.make_error(f"Type error: {e}")

        except Exception as e:
            return None, self.make_error(f"Unexpected error: {e}")

    def delete(self, driver):
        """
        Soft delete a driver by setting deleted_at and deleted_by.
        """
        driver.deleted_at = timezone.now()
        driver.deleted_by = self.auth_user
        driver.save()
        self.report_activity(ActivityType.delete, driver)
        return driver, None

    def hard_delete(self, driver):
        """
        Permanently delete a driver instance.
        """
        driver.delete()
        self.report_activity(ActivityType.delete, driver)
        return driver, None

    def check_exists(self, license_number=None) -> bool:
        if not license_number:
            return False

        return Driver.objects.filter(license_number__iexact=license_number).exists()

    def fetch_driver_by_user(self, user) -> (Driver, OperationError):
        def do_fetch():
            try:
                return self.get_queryset().get(user=user), None
            except Driver.DoesNotExist:
                return None, self.make_404(f"Driver User '{user}' not found")
            except Exception as e:
                return None, self.make_500(e)

        cache_key = self.generate_cache_key("driver", "user", user)
        return self.get_cache_value_or_default(cache_key, do_fetch)

    def get_queryset(self):
        return Driver.objects.select_related("user", "vehicle").order_by("-updated_at")

    def fetch_single(self, id) -> (Driver, OperationError):
        def do_fetch():
            try:
                return self.get_queryset().get(id=id), None
            except Driver.DoesNotExist:
                return None, self.make_404(f"Driver with id '{id}' not found")
            except Exception as e:
                return None, self.make_500(e)

        cache_key = self.generate_cache_key("driver", "id", id)
        return self.get_cache_value_or_default(cache_key, do_fetch)

    def clear_temp_cache(self, driver):
        self.clear_cache(self.generate_cache_key("driver", "id", driver.id))
        self.clear_cache(self.generate_cache_key("driver_id", driver.id))
