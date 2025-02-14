from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

#
#     path("register/rider", RegisterRiderView.as_view(), name="complete_registration"),
from accounts.controllers.auth import (
                                       ForgotPasswordRequestView, LoginView,
                                       RegisterDriverView, RegisterCustomerView,
                                       RegisterOtpView, ResetPasswordInAppRequestView,
                                       ResetPasswordRequestView, SignupView,
                                       VerifyOtpView)

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("signup", SignupView.as_view(), name="signup"),
    path("register/customer", RegisterCustomerView.as_view(),name="customer_registration"),
    path("register/driver", RegisterDriverView.as_view(), name="driver_registration"),
    path("signup/resend-otp", RegisterOtpView.as_view(), name="register-otp"),
    path("signup/verify-otp", VerifyOtpView.as_view(), name="verify-otp"),
    path("token/refresh", TokenRefreshView.as_view()),
    path("password/forgot", ForgotPasswordRequestView.as_view(), name="forgot-password"),
    path("password/change", ResetPasswordRequestView.as_view(), name="change-password"),
    path("password/in-app/change", ResetPasswordInAppRequestView.as_view(), name="change-password-in-app")


]
