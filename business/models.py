import uuid
from django.db import models

from accounts.models import User
from crm.models import BaseModel

class Vehicle(BaseModel):
    STATUS_REGULAR = "R"
    STATUS_COMFORT = "C"
    STATUS_EXOTIC = "E"
    STATUS_SUPER = "S"

    STATUS_CHOICES = [
        (STATUS_REGULAR, 'Regular'),
        (STATUS_COMFORT, 'Comfort'),
        (STATUS_EXOTIC,  'Exotic'),
        (STATUS_SUPER, 'Super')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    capacity = models.PositiveIntegerField(null=True, blank=True)
    grade = models.CharField(max_length=100)
    ride_type =  models.CharField(max_length=2, choices=STATUS_CHOICES, default=STATUS_REGULAR)

    
    def __str__(self):
        return f"{self.make} {self.model}"
    
class Driver(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)  
    license_number = models.CharField(
        max_length=255, null=True, blank=True
    )
    rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0, null=True, blank=True
    )  
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)

class Trip(BaseModel):
    STATUS_REQUESTED = 'R'
    STATUS_IN_PROGRESS = 'IP'
    STATUS_COMPLETED = 'C'
    STATUS_CANCELED = 'X'


    STATUS_CHOICES = [
        (STATUS_REQUESTED, 'Requested'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED,  'Completed'),
        (STATUS_CANCELED, 'Canceled')
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    start_location = models.CharField(
        max_length=400, null=True, blank=True
    ) 
    end_location = models.CharField(
        max_length=400, null=True, blank=True
    ) 
    distance = models.FloatField()
    fare_breakdown = models.JSONField(null=True, blank=True)
    total_fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default=STATUS_REQUESTED)
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

class TripReview(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    comment = models.TextField(null=True, blank=True)
