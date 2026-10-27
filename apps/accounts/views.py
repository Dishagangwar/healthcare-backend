from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from core.schema import error_response

from .serializers import (
    AuthResponseSerializer,
    LoginSerializer,
    ProfileResponseSerializer,
    RegisterSerializer,
    UserSerializer,
)


@extend_schema(
    tags=["auth"],
    summary="Register a new user",
    description=(
        "Creates an account from a name, email and password, and returns the user "
        "together with a JWT pair so no separate login call is needed.\n\n"
        "Passwords are checked against Django's validators: at least 8 characters, "
        "not a common password, not entirely numeric, and not similar to the name "
        "or email."
    ),
    responses={
        201: OpenApiResponse(AuthResponseSerializer, description="Account created."),
        400: error_response("400"),
    },
    examples=[
        OpenApiExample(
            "Registration",
            value={
                "name": "Disha Gupta",
                "email": "disha@example.com",
                "password": "StrongPass!234",
                "confirm_password": "StrongPass!234",
            },
            request_only=True,
        )
    ],
)
class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ - create an account and return a token pair."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "success": True,
                "message": "Account created successfully.",
                "data": {
                    "user": UserSerializer(user).data,
                    "tokens": LoginSerializer.build_tokens(user),
                },
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["auth"],
    summary="Log in and obtain a JWT pair",
    description=(
        "Exchanges an email and password for an access and refresh token.\n\n"
        "An unknown email and a wrong password return exactly the same error, so "
        "this endpoint cannot be used to discover which emails have accounts."
    ),
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(AuthResponseSerializer, description="Login successful."),
        400: error_response("400"),
    },
)
class LoginView(APIView):
    """POST /api/auth/login/ - exchange credentials for a JWT pair."""

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "data": {
                    "user": UserSerializer(user).data,
                    "tokens": LoginSerializer.build_tokens(user),
                },
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["auth"],
    summary="Refresh an access token",
    description=(
        "Returns a new access token for a valid refresh token. Refresh tokens "
        "rotate, so the response also carries a replacement refresh token.\n\n"
        "This endpoint comes from SimpleJWT and is the one place that responds "
        "without the standard envelope."
    ),
)
class RefreshView(TokenRefreshView):
    """POST /api/auth/refresh/ - trade a refresh token for a new access token."""

    permission_classes = [AllowAny]


@extend_schema(
    tags=["auth"],
    summary="Get the authenticated user",
    responses={
        200: OpenApiResponse(ProfileResponseSerializer, description="The current user."),
        401: error_response("401"),
    },
)
class ProfileView(generics.RetrieveAPIView):
    """GET /api/auth/profile/ - the authenticated user's own record."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        return Response(
            {"success": True, "data": self.get_serializer(self.get_object()).data},
            status=status.HTTP_200_OK,
        )
