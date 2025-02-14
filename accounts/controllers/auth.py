from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema
from rest_framework.generics import CreateAPIView, DestroyAPIView
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated

from accounts.models import RegisterLog, UserTypes
from accounts.serializers.auth import (DriverRegistrationSerializer,
                                      CustomerRegistrationSerializer, DriverRegistrationSerializer,
                                      EmailSerializer,
                                      ForgotPasswordRequestSerializer,
                                      LoginSerializer, OTPSerializer,
                                      ResendOtpSerializer, ResetPasswordInAppRequestSerializer,
                                      ResetPasswordRequestSerializer,
                                      SignupSerializer,
                                      VerifyAuthenticatorOtpSerializer,
                                      VerifyOtpSerializer)
from accounts.services.auth import AuthService
# from payment.services import PaymentService
from services.util import CustomApiRequestProcessorBase, user_type_required


class LoginView(TokenObtainPairView, CustomApiRequestProcessorBase):
    permission_classes = []
    authentication_classes = []
    serializer_class = LoginSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key="ip", rate="3/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.login)

class SignupView(CreateAPIView, CustomApiRequestProcessorBase):
    authentication_classes = []
    permission_classes = []
    serializer_class = SignupSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key="ip", rate="5/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.log_register)

class RegisterCustomerView(CreateAPIView, CustomApiRequestProcessorBase):
    authentication_classes = []
    permission_classes = []
    serializer_class = CustomerRegistrationSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key="ip", rate="5/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(
            request, service.register, register_type=UserTypes.customer
        )

class RegisterDriverView(CreateAPIView, CustomApiRequestProcessorBase):
    authentication_classes = []
    permission_classes = []
    serializer_class = DriverRegistrationSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key="ip", rate="5/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(
            request, service.register, register_type=UserTypes.driver
        )

class RegisterOtpView(CreateAPIView, CustomApiRequestProcessorBase):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResendOtpSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key="ip", rate="5/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.resend_registration_otp)

class VerifyOtpView(CreateAPIView, CustomApiRequestProcessorBase):
    authentication_classes = []
    permission_classes = []
    serializer_class = VerifyOtpSerializer

    @extend_schema(tags=["Auth"])
    @method_decorator(ratelimit(key="ip", rate="5/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.verify_register_otp)

class ResetPasswordRequestView(CreateAPIView, CustomApiRequestProcessorBase):
    serializer_class = ResetPasswordRequestSerializer
    authentication_classes = []
    permission_classes = []

    @method_decorator(ratelimit(key="ip", rate="5/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.reset_password)
    
class ResetPasswordInAppRequestView(CreateAPIView, CustomApiRequestProcessorBase):
    serializer_class = ResetPasswordInAppRequestSerializer
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="ip", rate="5/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.reset_password_in_app)

class ForgotPasswordRequestView(CreateAPIView, CustomApiRequestProcessorBase):
    serializer_class = ForgotPasswordRequestSerializer

    permission_classes = []
    authentication_classes = []

    @method_decorator(ratelimit(key="ip", rate="5/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.request_password_reset)

class GenerateOTPView(CreateAPIView, CustomApiRequestProcessorBase):
    permission_classes = []
    authentication_classes = []
    serializer_class = EmailSerializer

    @method_decorator(ratelimit(key="ip", rate="5/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.generate_authenticator_otp)

class VerifyAuthenticatorOTPView(CreateAPIView, CustomApiRequestProcessorBase):
    permission_classes = []
    authentication_classes = []
    serializer_class = VerifyAuthenticatorOtpSerializer

    @method_decorator(ratelimit(key="ip", rate="3/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.verify_authenticator_otp)

class ValidateAuthenticatorOTPView(CreateAPIView, CustomApiRequestProcessorBase):
    permission_classes = []
    authentication_classes = []

    @method_decorator(ratelimit(key="ip", rate="3/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.validate_authenticator_otp)

class GenerateEmailOTPAPIView(CreateAPIView, CustomApiRequestProcessorBase):
    permission_classes = []
    authentication_classes = []
    serializer_class = EmailSerializer

    @method_decorator(ratelimit(key="ip", rate="3/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.generate_email_otp)

class VerifyEmailOTPView(CreateAPIView, CustomApiRequestProcessorBase):
    permission_classes = []
    authentication_classes = []
    serializer_class = OTPSerializer

    @method_decorator(ratelimit(key="ip", rate="3/m"))
    def post(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.verify_email_otp)

class DisableOTPAPIView(DestroyAPIView, CustomApiRequestProcessorBase):
    serializer_class = EmailSerializer

    def delete(self, request, *args, **kwargs):
        service = AuthService(request)
        return self.process_request(request, service.disable_2fa)

