from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("auth/", include("api.urls.auth")),
    path('business/', include("api.urls.business"))
]