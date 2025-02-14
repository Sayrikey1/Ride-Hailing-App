import random
from django.core.management.base import BaseCommand

from business.models import Vehicle

class Command(BaseCommand):
    help = "Populate the Vehicle table with 30 real-life vehicles."

    def handle(self, *args, **options):
        vehicles_data = [
            {
                "make": "Toyota", "model": "Camry", "year": 2020, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Toyota", "model": "Corolla", "year": 2019, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Honda", "model": "Civic", "year": 2018, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Honda", "model": "Accord", "year": 2021, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_COMFORT
            },
            {
                "make": "Ford", "model": "Focus", "year": 2017, 
                "capacity": 5, "grade": "Hatchback", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Ford", "model": "Mustang", "year": 2022, 
                "capacity": 4, "grade": "Coupe", 
                "ride_type": Vehicle.STATUS_EXOTIC
            },
            {
                "make": "Chevrolet", "model": "Malibu", "year": 2018, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Nissan", "model": "Altima", "year": 2019, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_COMFORT
            },
            {
                "make": "BMW", "model": "3 Series", "year": 2020, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_SUPER
            },
            {
                "make": "BMW", "model": "X5", "year": 2021, 
                "capacity": 7, "grade": "SUV", 
                "ride_type": Vehicle.STATUS_SUPER
            },
            {
                "make": "Audi", "model": "A4", "year": 2020, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_COMFORT
            },
            {
                "make": "Audi", "model": "Q5", "year": 2021, 
                "capacity": 5, "grade": "SUV", 
                "ride_type": Vehicle.STATUS_COMFORT
            },
            {
                "make": "Mercedes-Benz", "model": "C-Class", "year": 2019, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_SUPER
            },
            {
                "make": "Mercedes-Benz", "model": "GLE", "year": 2020, 
                "capacity": 7, "grade": "SUV", 
                "ride_type": Vehicle.STATUS_SUPER
            },
            {
                "make": "Volkswagen", "model": "Golf", "year": 2018, 
                "capacity": 5, "grade": "Hatchback", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Volkswagen", "model": "Passat", "year": 2019, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Subaru", "model": "Impreza", "year": 2018, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Subaru", "model": "Outback", "year": 2020, 
                "capacity": 5, "grade": "Wagon", 
                "ride_type": Vehicle.STATUS_COMFORT
            },
            {
                "make": "Kia", "model": "Optima", "year": 2019, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Kia", "model": "Sorento", "year": 2021, 
                "capacity": 7, "grade": "SUV", 
                "ride_type": Vehicle.STATUS_COMFORT
            },
            {
                "make": "Hyundai", "model": "Sonata", "year": 2019, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Hyundai", "model": "Tucson", "year": 2020, 
                "capacity": 5, "grade": "SUV", 
                "ride_type": Vehicle.STATUS_COMFORT
            },
            {
                "make": "Mazda", "model": "6", "year": 2018, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Mazda", "model": "CX-5", "year": 2020, 
                "capacity": 5, "grade": "SUV", 
                "ride_type": Vehicle.STATUS_COMFORT
            },
            {
                "make": "Volvo", "model": "S60", "year": 2019, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_REGULAR
            },
            {
                "make": "Volvo", "model": "XC90", "year": 2021, 
                "capacity": 7, "grade": "SUV", 
                "ride_type": Vehicle.STATUS_SUPER
            },
            {
                "make": "Jeep", "model": "Wrangler", "year": 2020, 
                "capacity": 4, "grade": "SUV", 
                "ride_type": Vehicle.STATUS_EXOTIC
            },
            {
                "make": "Land Rover", "model": "Range Rover", "year": 2021, 
                "capacity": 5, "grade": "SUV", 
                "ride_type": Vehicle.STATUS_SUPER
            },
            {
                "make": "Porsche", "model": "911", "year": 2022, 
                "capacity": 4, "grade": "Coupe", 
                "ride_type": Vehicle.STATUS_EXOTIC
            },
            {
                "make": "Tesla", "model": "Model S", "year": 2021, 
                "capacity": 5, "grade": "Sedan", 
                "ride_type": Vehicle.STATUS_SUPER
            }
        ]

        created_count = 0
        for data in vehicles_data:
            Vehicle.objects.create(**data)
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully created {created_count} vehicles."))
