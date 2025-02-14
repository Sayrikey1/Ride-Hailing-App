import random
import string
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from accounts.models import User, UserTypes, RegisterLog
from unittest.mock import patch

def get_random_first_last_name():
    first_names = [
        "Alice", "Bob", "Charlie", "David", "Eva", "Frank", "Grace", "Hannah", "Ian", "Jack",
        "Katherine", "Liam", "Mia", "Noah", "Olivia", "Pamela", "Quincy", "Rachel", "Sam", "Tina",
        "Uma", "Victor", "Wendy", "Xander", "Yara", "Zach", "Aaron", "Bella", "Connor", "Diana"
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson",
        "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez", "Moore", "Martin", "Jackson", "Thompson", "White",
        "Lopez", "Lee", "Gonzalez", "Harris", "Clark", "Lewis", "Robinson", "Walker", "Perez", "Hall"
    ]
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    random_suffix = ''.join(random.choices(string.digits, k=3))
    full_name = f"{first_name} {last_name}"
    email = f"{first_name.lower()}.{last_name.lower()}{random_suffix}@gmail.com"
    username = f"{first_name.lower()}{last_name.lower()}{random_suffix}"
    return first_name, last_name, full_name, email, username

class AuthViewsTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # Patch the activation OTP email task so it doesn't try to connect to the broker.
        self.email_task_patcher = patch('accounts.services.auth.send_activation_otp_email_queue.delay', return_value=None)
        self.mock_send_activation_otp = self.email_task_patcher.start()

    def tearDown(self):
        self.email_task_patcher.stop()

    def test_full_auth_flow_customer(self):
        """
        Full flow for a customer:
         1. Signup
         2. Verify OTP via the verify OTP endpoint
         3. Complete registration as a customer (with required fields)
         4. Login using real JWT auth
        """
        # Generate random user data.
        first_name, last_name, full_name, customer_email, customer_username = get_random_first_last_name()
        password = "Customer@1234"  # valid password

        # 1. Signup
        signup_url = reverse("signup")
        signup_payload = {
            "email": customer_email,
            "full_name": full_name,
            "password": password,
            "device_id": "dummy_device_id",
            "device_name": "dummy_device_name"
        }
        signup_response = self.client.post(signup_url, signup_payload, format="json")
        self.assertEqual(
            signup_response.status_code, status.HTTP_200_OK,
            f"Signup failed: {signup_response.content}"
        )
        self.assertIn("message", signup_response.data)
        self.assertIn("data", signup_response.data)
        self.assertEqual(signup_response.data["data"].get("email"), customer_email)

        # 2. Verify OTP using the verify OTP endpoint.
        verify_url = reverse("verify-otp")
        verify_payload = {"email": customer_email, "otp": "123456"}
        with patch('accounts.services.auth.compare_password', return_value=True):
            verify_response = self.client.post(verify_url, verify_payload, format="json")
        self.assertEqual(
            verify_response.status_code, status.HTTP_200_OK,
            f"OTP verification failed: {verify_response.content}"
        )

        # 3. Complete registration as a customer.
        register_customer_url = reverse("customer_registration")
        register_payload = {
            "email": customer_email,
            "username": customer_username,
            "full_name": full_name,
            "password": password,
            "phone_number": "+2347012245678",  
            "gender": "Male",
            "dob": "1990-01-01"
        }
        register_response = self.client.post(register_customer_url, register_payload, format="json")
        self.assertEqual(
            register_response.status_code, status.HTTP_200_OK,
            f"Customer registration failed: {register_response.content}"
        )
        self.assertIn("message", register_response.data)
        self.assertIn("fcm_token", register_response.data)

        # 4. Login using real JWT auth.
        login_url = reverse("login")
        login_payload = {
            "username": customer_username,
            "password": password,
            "fcm_token": "dummy_fcm_token",      
            "device_id": "dummy_device_id",        
            "device_name": "dummy_device_name"    
        }
        login_response = self.client.post(login_url, login_payload, format="json")
        self.assertEqual(
            login_response.status_code, status.HTTP_200_OK,
            f"Login failed: {login_response.content}"
        )
        data = login_response.data
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    def test_full_auth_flow_driver(self):
        """
        Full flow for a driver:
         1. Signup
         2. Verify OTP via the verify OTP endpoint
         3. Complete registration as a driver (with required fields)
         4. Login using real JWT auth
        """
        # Generate random user data.
        first_name, last_name, full_name, driver_email, driver_username = get_random_first_last_name()
        password = "Driver@1234"  # valid password

        # 1. Signup
        signup_url = reverse("signup")
        signup_payload = {
            "email": driver_email,
            "full_name": full_name,
            "password": password,
            "device_id": "dummy_device_id",
            "device_name": "dummy_device_name"
        }
        signup_response = self.client.post(signup_url, signup_payload, format="json")
        self.assertEqual(
            signup_response.status_code, status.HTTP_200_OK,
            f"Signup failed: {signup_response.content}"
        )
        self.assertIn("data", signup_response.data)
        self.assertEqual(signup_response.data["data"].get("email"), driver_email)

        # 2. Verify OTP using the verify OTP endpoint.
        verify_url = reverse("verify-otp")
        verify_payload = {"email": driver_email, "otp": "123456"}
        with patch('accounts.services.auth.compare_password', return_value=True):
            verify_response = self.client.post(verify_url, verify_payload, format="json")
        self.assertEqual(
            verify_response.status_code, status.HTTP_200_OK,
            f"OTP verification failed: {verify_response.content}"
        )

        # 3. Complete registration as a driver.
        register_driver_url = reverse("driver_registration")
        license_number = "LIC-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        register_payload = {
            "email": driver_email,
            "username": driver_username,
            "full_name": full_name,
            "password": password,
            "phone_number": "+2347012245678",  # Nigerian phone style
            "gender": "Male",
            "dob": "1990-01-01",
            "license_number": license_number
        }
        register_response = self.client.post(register_driver_url, register_payload, format="json")
        self.assertEqual(
            register_response.status_code, status.HTTP_200_OK,
            f"Driver registration failed: {register_response.content}"
        )
        self.assertIn("message", register_response.data)
        self.assertIn("fcm_token", register_response.data)

        # 4. Login using real JWT auth.
        login_url = reverse("login")
        login_payload = {
            "username": driver_username,
            "password": password,
            "fcm_token": "dummy_fcm_token",     
            "device_id": "dummy_device_id",       
            "device_name": "dummy_device_name"    
        }
        login_response = self.client.post(login_url, login_payload, format="json")
        self.assertEqual(
            login_response.status_code, status.HTTP_200_OK,
            f"Login failed: {login_response.content}"
        )
        data = login_response.data
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
