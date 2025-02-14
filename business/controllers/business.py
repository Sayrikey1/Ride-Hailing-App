from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from accounts.models import User
from business.models import Vehicle, Driver, Trip, TripReview
from business.serializers import (
    CalculateFareSerializer,
    CreateTripSerializer,
    TripReviewSerializer,
    TripSerializer,
    VehicleSerializer,
)
from business.util import PricingConfig, calculate_trip_fare, get_random_pricing_multipliers
from services.location import LocationService
from services.util import CustomApiRequestProcessorBase


pricing_config = PricingConfig()


class CreateTripView(APIView, CustomApiRequestProcessorBase):
    serializer_class = CreateTripSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        def create_trip(validated_data, **extra_args):
            customer = User.objects.filter(id=request.user.id).first()

            if not customer:
                return None, "User not found"
            
            driver = validated_data['driver']
            driver = Driver.objects.filter(id=driver.id).first()

            if not driver:
                return None, "Driver not found"
            
            start_loc = validated_data['start_location']
            end_loc = validated_data['end_location']
            
            distance = LocationService().calculate_distance(start_loc, end_loc)
            validated_data['distance'] = distance
            validated_data['customer'] = customer
            trip = Trip.objects.create(**validated_data)

            # In a production system, the current conditions (e.g., traffic, demand)
            # would be determined by querying real-time logs from the backend.
            # Since that data isn't available here, we simulate these conditions
            # prior to calculating the fare.

            random_multipliers = get_random_pricing_multipliers(pricing_config)

            traffic = random_multipliers.get("traffic_multiplier", {})
            surge = random_multipliers.get("demand_surge_pricing", {})
            time_of_day = random_multipliers.get("time_of_day_factor", {})
            weather = random_multipliers.get("weather_condition_factor", {})
            ride = random_multipliers.get("ride_type_factor", {})
            event = random_multipliers.get("special_event_pricing", {})

            # Calculate fare safely
            total, breakdown = calculate_trip_fare(
                trip,
                pricing_config,
                traffic_key=traffic.get("state", "default"),    
                surge_key=surge.get("state", "default"),     
                time_of_day_key=time_of_day.get("state", "default")
            )

            return {
                "total": total,  # Fixed typo from 'totat' to 'total'
                "breakdown": breakdown
            }, None

        return self.process_request(request, create_trip)


class CreateVehicleAPIView(APIView, CustomApiRequestProcessorBase):
    serializer_class = VehicleSerializer
    def post(self, request, *args, **kwargs):
        def create_vehicle(validated_data):
            vehicle_instance = Vehicle.objects.create(**validated_data)
            serialized_vehicle = VehicleSerializer(vehicle_instance).data
            return serialized_vehicle, None
        return self.process_request(request, create_vehicle)


class CreateTripReviewAPIView(APIView, CustomApiRequestProcessorBase):
    serializer_class = TripReviewSerializer

    def post(self, request, *args, **kwargs):
        def create_trip_review(validated_data):
            trip_review_instance = TripReview.objects.create(**validated_data)
            serialized_trip_review = TripReviewSerializer(trip_review_instance).data
            return serialized_trip_review, None

        return self.process_request(request, create_trip_review)


class ListDriverTripsAPIView(APIView, CustomApiRequestProcessorBase):
    """
    GET trips for a specific driver.
    Expects a query parameter `driver_id`. Example: /api/driver-trips/?driver_id=<uuid>
    """
    def get(self, request, *args, **kwargs):
        def get_trips():
            user = request.user
            try:
                driver = Driver.objects.get(user=user)
            except ObjectDoesNotExist:
                return None, "Driver does not exist"
        
            trips = Trip.objects.filter(driver__id=driver.id)
            serializer = TripSerializer(trips, many=True)
            return serializer.data, None
        return self.process_request(request, get_trips)


class ListUserTripsAPIView(APIView, CustomApiRequestProcessorBase):
    """
    GET trips for the authenticated user (as customer).
    Ensure that the user is authenticated.
    """
    def get(self, request, *args, **kwargs):
        def get_trips():
            user = request.user
            trips = Trip.objects.filter(customer=user)
            serializer = TripSerializer(trips, many=True)
            return serializer.data, None
        return self.process_request(request, get_trips)


class CalculateFareView(APIView, CustomApiRequestProcessorBase):
    permission_classes = [AllowAny]
    serializer_class = CalculateFareSerializer

    def post(self, request, *args, **kwargs):
        def calculate(validated_data, **extra_args):
            # Extract validated data.
            distance = validated_data["distance"]
            traffic_level = validated_data.get("traffic_level", "low")
            demand_level = validated_data.get("demand_level", "low")
            
            # Pricing parameters.
            base_fare = 2.5
            per_km_rate = 1.0
            distance_fare = distance * per_km_rate

            # Define multipliers.
            traffic_config = {
                "low": 1.0,
                "moderate": 1.2,
                "high": 1.5,
            }
            demand_config = {
                "low": 1.0,
                "moderate": 1.2,
                "peak": 1.8,
                "extreme": 2.5,
            }
            traffic_multiplier = traffic_config.get(traffic_level, 1.0)
            demand_multiplier = demand_config.get(demand_level, 1.0)
            
            # Calculate total fare.
            total_fare = (base_fare + distance_fare) * traffic_multiplier * demand_multiplier
            total_fare = round(total_fare, 2)

            data = {
                "base_fare": base_fare,
                "distance_fare": distance_fare,
                "traffic_multiplier": traffic_multiplier,
                "demand_multiplier": demand_multiplier,
                "total_fare": total_fare
            }
            return data, None

        return self.process_request(request, calculate)