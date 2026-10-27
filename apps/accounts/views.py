from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


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


class RefreshView(TokenRefreshView):
    """POST /api/auth/refresh/ - trade a refresh token for a new access token."""

    permission_classes = [AllowAny]


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
