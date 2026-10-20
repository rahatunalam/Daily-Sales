from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import User
from .permissions import IsOwner
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileSerializer,
    UserSerializer,
)


class LoginView(APIView):
    """Sign in with name + password. Returns a token and the profile."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: dict})
    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "profile": ProfileSerializer(user).data})


class LogoutView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Profile menu: name and designation."""

    @extend_schema(responses=ProfileSerializer)
    def get(self, request):
        return Response(ProfileSerializer(request.user).data)


class ChangePasswordView(APIView):
    @extend_schema(request=ChangePasswordSerializer, responses={200: dict})
    def post(self, request):
        s = ChangePasswordSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        request.user.set_password(s.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        Token.objects.filter(user=request.user).delete()  # old token stops working
        token = Token.objects.create(user=request.user)
        return Response({"detail": "Password changed.", "token": token.key})


class UserViewSet(viewsets.ModelViewSet):
    """Settings > Add User (owner only)."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsOwner]
    http_method_names = ["get", "post", "patch", "head", "options"]

    @extend_schema(request=None, responses=UserSerializer)
    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response({"detail": "You cannot deactivate yourself."}, status=400)
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        if not user.is_active:
            Token.objects.filter(user=user).delete()
        return Response(UserSerializer(user).data)
