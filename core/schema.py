"""OpenAPI schema generation tuned to this API's response envelopes.

Views return `{"success": true, "data": ...}` via `core.mixins`, and errors
return `{"success": false, "error": {...}}` via `core.exceptions`. Left alone,
drf-spectacular would document the bare serializer, so the published schema
would not match a single real response. `EnvelopeAutoSchema` applies both
envelopes during generation instead of annotating every view by hand, which
keeps the docs correct as endpoints are added.
"""

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiResponse

from core.mixins import StandardResponseMixin


def is_schema_generation(view):
    """True while drf-spectacular is introspecting this view, not serving it.

    Generation runs without a real request, so `request.user` is anonymous and
    any queryset filtered by owner would raise. Owner-scoped views return an
    empty queryset in that case; the model is all the generator needs.
    """
    return getattr(view, "swagger_fake_view", False)

# Error codes from core.exceptions.ERROR_CODES, by the status they ride on.
ERROR_EXAMPLES = {
    "400": ("validation_error", "phone: Enter a valid phone number.",
            {"phone": ["Enter a valid phone number."]}),
    "401": ("not_authenticated",
            "Authentication credentials were not provided or are invalid.", None),
    "403": ("permission_denied", "You do not have permission to act on this record.", None),
    "404": ("not_found", "The requested resource was not found.", None),
    "409": ("integrity_error",
            "The request conflicts with the current state of the resource.", None),
}


def _error_schema(status_code):
    code, message, details = ERROR_EXAMPLES[status_code]
    properties = {
        "code": {"type": "string", "example": code,
                 "description": "Stable identifier to branch on."},
        "message": {"type": "string", "example": message,
                    "description": "Human-readable summary, displayable as-is."},
    }
    if details is not None:
        properties["details"] = {
            "type": "object",
            "additionalProperties": {"type": "array", "items": {"type": "string"}},
            "example": details,
            "description": "Per-field errors, for attaching to form inputs.",
        }
    return {
        "type": "object",
        "required": ["success", "error"],
        "properties": {
            "success": {"type": "boolean", "example": False},
            "error": {"type": "object", "required": ["code", "message"],
                      "properties": properties},
        },
    }


def error_response(status_code):
    """An OpenApiResponse carrying the error envelope for `status_code`.

    For views that declare `responses=` explicitly and would otherwise lose the
    error shapes that EnvelopeAutoSchema adds automatically.
    """
    return OpenApiResponse(
        response=_error_schema(status_code),
        description=ERROR_EXAMPLES[status_code][1],
    )


def _is_already_enveloped(schema):
    """True when a view documented its own response with `success` at the top."""
    return isinstance(schema, dict) and "success" in schema.get("properties", {})


class EnvelopeAutoSchema(AutoSchema):
    """Wraps generated responses in this API's success and error envelopes."""

    def _get_response_for_code(self, serializer, status_code, media_types=None,
                               direction="response"):
        response = super()._get_response_for_code(
            serializer, status_code, media_types, direction
        )

        if not str(status_code).startswith("2") or "content" not in response:
            return response

        # Only views that render through StandardResponseMixin carry the
        # envelope. Anything else -- notably SimpleJWT's token refresh, which
        # returns a bare {"access": ...} -- must be documented as it really
        # responds. Views that build an envelope by hand declare their own
        # response serializer via @extend_schema.
        if not isinstance(self.view, StandardResponseMixin):
            return response

        # A paginated list response is built by
        # StandardResultsPagination.get_paginated_response_schema, which
        # already carries the envelope. It is emitted as a $ref to a
        # "Paginated*" component, so inspecting the resolved shape here would
        # see nothing and wrap it a second time; mirror the condition
        # drf-spectacular itself uses to decide on pagination instead.
        if self._is_paginated_list(serializer):
            return response

        for media_type, content in response["content"].items():
            schema = content.get("schema")
            if schema is None or _is_already_enveloped(schema):
                continue
            # A paginated list already carries the envelope from
            # StandardResultsPagination.get_paginated_response_schema.
            if schema.get("type") == "object" and "results" in schema.get("properties", {}):
                continue

            properties = {"success": {"type": "boolean", "example": True}}
            if str(status_code) in ("200", "201") and self.method in ("POST", "PUT", "PATCH"):
                properties["message"] = {
                    "type": "string", "example": "Patient created successfully.",
                    "description": "Confirmation text, safe to surface to the user.",
                }
            properties["data"] = schema

            content["schema"] = {
                "type": "object",
                "required": ["success", "data"],
                "properties": properties,
            }

        return response

    def _is_paginated_list(self, serializer):
        if self.method != "GET" or getattr(self.view, "paginator", None) is None:
            return False
        try:
            return bool(self._is_list_view(serializer))
        except TypeError:          # older signature takes no serializer
            return bool(self._is_list_view())

    def _get_response_bodies(self, direction="response"):
        responses = super()._get_response_bodies(direction)

        # DELETE returns the envelope with a message and no data.
        if self.method == "DELETE" and "204" in responses:
            responses.pop("204")
            responses["200"] = {
                "description": "Deleted.",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["success", "message"],
                            "properties": {
                                "success": {"type": "boolean", "example": True},
                                "message": {"type": "string",
                                            "example": "Patient deleted successfully."},
                            },
                        }
                    }
                },
            }

        for status_code in self._error_codes_for_operation():
            responses.setdefault(status_code, {
                "description": ERROR_EXAMPLES[status_code][1],
                "content": {"application/json": {"schema": _error_schema(status_code)}},
            })
        return responses

    def _error_codes_for_operation(self):
        """Which failures this particular operation can realistically return."""
        codes = []
        if self.method in ("POST", "PUT", "PATCH"):
            codes.append("400")

        view = self.view
        permission_classes = getattr(view, "permission_classes", [])
        is_public = any(
            getattr(cls, "__name__", "") == "AllowAny" for cls in permission_classes
        )
        if not is_public:
            codes.append("401")
            # Only object-level ownership checks produce a 403; elsewhere the
            # queryset is filtered by owner, so a miss is a 404 instead.
            if any(getattr(cls, "__name__", "") == "IsOwner" for cls in permission_classes):
                codes.append("403")

        if "{id}" in (self.path or "") or "{pk}" in (self.path or ""):
            codes.append("404")
        return codes
