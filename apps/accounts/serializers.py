from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Read-only shape of a user, returned alongside auth tokens."""

    class Meta:
        model = User
        fields = ["id", "name", "email", "date_joined"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}, trim_whitespace=False
    )
    confirm_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}, trim_whitespace=False
    )

    class Meta:
        model = User
        fields = ["id", "name", "email", "password", "confirm_password"]
        extra_kwargs = {
            "name": {"required": True, "allow_blank": False},
            "email": {"required": True},
        }

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate_name(self, value):
        name = value.strip()
        if len(name) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long.")
        return name

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "The two password fields do not match."}
            )
        # Run Django's configured password validators against the real user
        # fields so similarity checks (name/email) apply too.
        candidate = User(name=attrs.get("name", ""), email=attrs.get("email", ""))
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data["name"],
        )


class LoginSerializer(serializers.Serializer):
    """Validates credentials and hands back a JWT pair."""

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}, trim_whitespace=False
    )

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"].lower().strip(),
            password=attrs["password"],
        )
        if user is None:
            # Deliberately identical for unknown email and wrong password so
            # the endpoint cannot be used to enumerate registered accounts.
            raise serializers.ValidationError(
                {"non_field_errors": "Invalid email or password."}
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {"non_field_errors": "This account has been deactivated."}
            )
        attrs["user"] = user
        return attrs

    @staticmethod
    def build_tokens(user):
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="Send as 'Authorization: Bearer <access>'.")
    refresh = serializers.CharField(help_text="Use at /api/auth/refresh/ for a new access token.")


class AuthPayloadSerializer(serializers.Serializer):
    user = UserSerializer()
    tokens = TokenPairSerializer()


class AuthResponseSerializer(serializers.Serializer):
    """Shape of a successful register or login response."""

    success = serializers.BooleanField(default=True)
    message = serializers.CharField(default="Login successful.")
    data = AuthPayloadSerializer()


class ProfileResponseSerializer(serializers.Serializer):
    """Shape of a successful profile response."""

    success = serializers.BooleanField(default=True)
    data = UserSerializer()
