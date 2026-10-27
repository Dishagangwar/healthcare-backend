from django.core.validators import RegexValidator

PHONE_VALIDATOR = RegexValidator(
    regex=r"^\+?[0-9]{7,15}$",
    message="Enter a valid phone number: 7-15 digits, optionally prefixed with '+'.",
)
