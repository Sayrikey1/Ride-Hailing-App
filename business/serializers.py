from rest_framework import serializers
from business.models import Vehicle, Driver, Trip, TripReview

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            'id',
            'make',
            'model',
            'year',
            'capacity'
        ]

class DriverSerializer(serializers.ModelSerializer):
    vehicle = VehicleSerializer(read_only=True)
    class Meta:
        model = Driver
        fields = [
            'id',
            'user',
            'license_number',
            'rating',
            'vehicle',
        ]

class TripReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripReview
        fields = [
            'id',
            'trip',
            'reviewer'
        ]

class CreateTripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = [
            'id',
            'driver',
            'start_location',
            'end_location',
            'status',
            'requested_at',
        ]

class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = [
            'id',
            'customer',
            'driver',
            'start_location',
            'end_location',
            'distance',
            'fare_breakdown',
            'total_fare',
            'status',
            'requested_at',
            'started_at',
            'ended_at',
            'reviews'
        ]

class CalculateFareSerializer(serializers.Serializer):
    distance = serializers.FloatField(required=True, min_value=0)
    traffic_level = serializers.ChoiceField(
        choices=[("low", "low"), ("moderate", "moderate"), ("high", "high")],
        default="low"
    )
    demand_level = serializers.ChoiceField(
        choices=[("low", "low"), ("moderate", "moderate"), ("peak", "peak"), ("extreme", "extreme")],
        default="low"
    )
