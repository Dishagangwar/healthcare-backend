import logging

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

ERROR_CODES = {
    exceptions.ParseError: "parse_error",
    exceptions.AuthenticationFailed: "authentication_failed",
    exceptions.NotAuthenticated: "not_authenticated",
    exceptions.PermissionDenied: "permission_denied",
    exceptions.NotFound: "not_found",
    exceptions.MethodNotAllowed: "method_not_allowed",
    exceptions.NotAcceptable: "not_acceptable",
    exceptions.UnsupportedMediaType: "unsupported_media_type",
    exceptions.Throttled: "throttled",
    exceptions.ValidationError: "validation_error",
}

DEFAULT_MESSAGES = {
    status.HTTP_400_BAD_REQUEST: "The request could not be processed.",
    status.HTTP_401_UNAUTHORIZED: "Authentication credentials were not provided or are invalid.",
    status.HTTP_403_FORBIDDEN: "You do not have permission to perform this action.",
    status.HTTP_404_NOT_FOUND: "The requested resource was not found.",
    status.HTTP_405_METHOD_NOT_ALLOWED: "This method is not allowed on this endpoint.",
    status.HTTP_409_CONFLICT: "The request conflicts with the current state of the resource.",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "An unexpected error occurred.",
}


def _build_payload(code, message, details=None):
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"success": False, "error": error}


def _flatten_detail(detail):
    """Turn a DRF `detail` structure into (message, details).

    DRF hands back a string, a list, or a dict keyed by field name. Field
    errors stay in `details` so clients can attach them to inputs; the
    top-level `message` is a single human-readable summary.
    """
    if isinstance(detail, dict):
        details = {
            field: errors if isinstance(errors, list) else [errors]
            for field, errors in detail.items()
        }
        first_field, first_errors = next(iter(details.items()))
        label = "" if first_field == "non_field_errors" else f"{first_field}: "
        return f"{label}{first_errors[0]}", details
    if isinstance(detail, list):
        flat = [str(item) for item in detail]
        return flat[0], {"non_field_errors": flat}
    return str(detail), None


def custom_exception_handler(exc, context):
    """Render every API error in one envelope: {success, error:{code,message,details?}}.

    Wired in via REST_FRAMEWORK["EXCEPTION_HANDLER"]. Django-native
    exceptions are translated to their DRF equivalents first so that a
    model's `full_clean()` and a serializer's `validate()` surface
    identically to the client.
    """
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, IntegrityError):
        # A race or a constraint the serializer could not pre-check.
        logger.warning("Database integrity error: %s", exc, exc_info=True)
        return Response(
            _build_payload("integrity_error", DEFAULT_MESSAGES[status.HTTP_409_CONFLICT]),
            status=status.HTTP_409_CONFLICT,
        )

    response = drf_exception_handler(exc, context)

    if response is None:
        # Nothing DRF recognises: log the traceback, tell the client nothing.
        logger.exception("Unhandled exception in %s", context.get("view"))
        return Response(
            _build_payload("server_error", DEFAULT_MESSAGES[status.HTTP_500_INTERNAL_SERVER_ERROR]),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = ERROR_CODES.get(type(exc), getattr(exc, "default_code", "error"))
    message, details = _flatten_detail(response.data.get("detail", response.data)
                                      if isinstance(response.data, dict) else response.data)
    if not message:
        message = DEFAULT_MESSAGES.get(response.status_code, "Request failed.")

    response.data = _build_payload(code, message, details)
    return response
