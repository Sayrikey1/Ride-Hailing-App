import uuid
import random
from django.core.management.base import BaseCommand
from accounts.models import User
from business.models import Driver, Vehicle

class Command(BaseCommand):
    help = "Create Driver objects for all users with user_type='Driver', update missing license numbers, and assign vehicles if missing."

    def handle(self, *args, **kwargs):
        drivers = User.objects.filter(user_type="Driver")
        created_count = 0
        updated_license_count = 0
        vehicle_assigned_count = 0

        # Fetch existing vehicles from the database.
        vehicles = list(Vehicle.objects.all())
        if not vehicles:
            self.stdout.write(self.style.WARNING("No vehicles found in the database. Drivers will not be assigned vehicles."))

        for user in drivers:
            driver, created = Driver.objects.get_or_create(user=user)

            # Generate a license number if missing.
            if not driver.license_number:
                driver.license_number = f"DRV-{uuid.uuid4().hex[:10].upper()}"
                driver.save(update_fields=["license_number"])
                if not created:
                    updated_license_count += 1

            # Assign a vehicle if none is assigned and vehicles exist.
            if not driver.vehicle and vehicles:
                driver.vehicle = random.choice(vehicles)
                driver.save(update_fields=["vehicle"])
                vehicle_assigned_count += 1

            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully created {created_count} Driver objects, updated {updated_license_count} drivers with license numbers, "
            f"and assigned vehicles to {vehicle_assigned_count} drivers."
        ))
