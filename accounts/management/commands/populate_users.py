import uuid
import random

from django.core.management.base import BaseCommand
from accounts.models import User, UserTypes


class Command(BaseCommand):
    help = 'Populates the User model with test data. For every 5 users, 1 is a Driver.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='The total number of users to create (default is 50).'
        )

    def handle(self, *args, **options):
        count = options['count']
        created = 0

        for i in range(1, count + 1):
            # For every 5 users, 1 should be a driver.
            # (i.e. users 5, 10, 15, etc. will be drivers)
            if i % 5 == 0:
                user_type = UserTypes.driver  # "Driver"
            else:
                user_type = UserTypes.customer  # "Customer"

            username = f"testuser{i}"
            email = f"testuser{i}@egmail.com"
            full_name = f"Test User {i}"

            # Create the user using Django's create_user helper which hashes the password.
            user = User.objects.create_user(
                username=username,
                email=email,
                password="password123",  # Dummy password
                full_name=full_name,
                user_type=user_type,
                country="Testland",  # Dummy country
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully created {created} users."))
