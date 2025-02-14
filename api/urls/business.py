from django.urls import include, path

from business.controllers.business import (
    CalculateFareView,
    CreateTripView,
    CreateVehicleAPIView,
    CreateTripReviewAPIView,
    ListDriverTripsAPIView,
    ListUserTripsAPIView
)

urlpatterns = [
    path('trips/create/', CreateTripView.as_view(), name='create-trip'),
    # path('vehicles/create/', CreateVehicleAPIView.as_view(), name='create-vehicle'),
    path('trips/review/', CreateTripReviewAPIView.as_view(), name='create-trip-review'),
    path('trips/driver/', ListDriverTripsAPIView.as_view(), name='list-driver-trips'),
    path('trips/user/', ListUserTripsAPIView.as_view(), name='list-user-trips'),
    path('calculate-fare/', CalculateFareView.as_view(), name='calculate-fare')
]
