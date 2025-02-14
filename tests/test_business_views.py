import random
import string
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from business.models import Driver, Trip

User = get_user_model()

class TripViewsTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # Generate random customer and driver users for each test run.
        self.customer = User.objects.create_user(
            username=self.get_random_string("cust"),
            email=self.get_random_email("cust"),
            password="Password@1234"
        )
        self.driver_user = User.objects.create_user(
            username=self.get_random_string("driv"),
            email=self.get_random_email("driv"),
            password="Password@1234",
            user_type="Driver"
        )
        self.driver = Driver.objects.create(user=self.driver_user, license_number="LIC-EXIST", vehicle=None)

        # Monkey-patch external dependencies.
        from services.location import LocationService  
        self.original_calculate_distance = LocationService.calculate_distance
        LocationService.calculate_distance = lambda self, start, end: 10

        import business.util
        self.original_get_random_pricing_multipliers = business.util.get_random_pricing_multipliers
        business.util.get_random_pricing_multipliers = lambda config: {
            "traffic_multiplier": {"state": "low"},
            "demand_surge_pricing": {"state": "low"},
            "time_of_day_factor": {"state": "off_peak"},
            "weather_condition_factor": {"state": "clear"},
            "ride_type_factor": {"state": "economy"},
            "special_event_pricing": {"state": "normal"}
        }

    def tearDown(self):
        from services.location import LocationService  
        LocationService.calculate_distance = self.original_calculate_distance
        import business.util
        business.util.get_random_pricing_multipliers = self.original_get_random_pricing_multipliers

    def get_random_string(self, prefix):
        return prefix + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

    def get_random_email(self, prefix):
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{prefix}{random_suffix}@gmail.com"

    def test_create_trip_view(self):
        """
        Test the CreateTripView endpoint by simulating a POST request to create a trip.
        Uses "University of Lagos" as start location and "Bariga" as end location.
        """
        # Authenticate as the customer.
        self.client.force_authenticate(user=self.customer)
        payload = {
            "driver": str(self.driver.id),  # Assuming the serializer accepts the driver's id as a string.
            "start_location": "University of Lagos",
            "end_location": "Bariga",
            "status": "R",  # e.g. "R" for Regular.
        }
        url = reverse("create-trip")
        response = self.client.post(url, payload, format="json")
        self.assertEqual(
            response.status_code, status.HTTP_200_OK,
            f"Create trip failed: {response.content}"
        )
        data = response.data
        self.assertIn("total", data)
        self.assertIn("breakdown", data)
        try:
            total = Decimal(data["total"])
            self.assertTrue(total >= 0)
        except Exception:
            self.fail("Total fare is not a valid number.")

    def test_list_driver_trips_view(self):
        """
        Test the ListDriverTripsAPIView endpoint by retrieving trips for a driver.
        """
        # Create a sample trip for the driver.
        trip = Trip.objects.create(
            driver=self.driver,
            customer=self.customer,
            start_location="University of Lagos",
            end_location="Bariga",
            distance=10,
            status="R"
        )
        url = reverse("list-driver-trips")
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.get(url, format="json")
        self.assertEqual(
            response.status_code, status.HTTP_200_OK,
            f"Listing driver trips failed: {response.content}"
        )
        # Extract the list from the response.
        data = response.data.get("data", response.data)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    def test_list_user_trips_view(self):
        """
        Test the ListUserTripsAPIView endpoint by retrieving trips for a customer.
        """
        # Create a sample trip for the customer.
        trip = Trip.objects.create(
            driver=self.driver,
            customer=self.customer,
            start_location="University of Lagos",
            end_location="Bariga",
            distance=10,
            status="R"
        )
        url = reverse("list-user-trips")
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(url, format="json")
        self.assertEqual(
            response.status_code, status.HTTP_200_OK,
            f"Listing user trips failed: {response.content}"
        )
        # Extract the list from the response.
        data = response.data.get("data", response.data)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
