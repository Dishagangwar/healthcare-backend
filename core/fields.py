import re

from rest_framework import serializers

SEPARATORS = re.compile(r"[\s\-().]")


class PhoneNumberField(serializers.CharField):
    """A phone number, normalised before its format is checked.

    DRF runs `to_internal_value()` ahead of the field's validators, so
    stripping separators here means a human-entered "+91 98123-45678" is
    accepted and stored as "+919812345678" rather than being rejected by the
    regex. Normalising in `validate_<field>()` instead would be too late.
    """

    def to_internal_value(self, data):
        return SEPARATORS.sub("", super().to_internal_value(data))
