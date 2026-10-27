from rest_framework import status
from rest_framework.response import Response


class StandardResponseMixin:
    """Wraps generic-view responses in {"success": true, "data": ...}.

    Errors get the matching shape from core.exceptions, and paginated lists
    from core.pagination, so every response in the API reads the same way.
    `resource_name` tunes the message text on write operations.
    """

    resource_name = "Record"

    def _envelope(self, data, message=None, http_status=status.HTTP_200_OK):
        payload = {"success": True}
        if message:
            payload["message"] = message
        payload["data"] = data
        return Response(payload, status=http_status)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            # StandardResultsPagination already supplies the envelope.
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return self._envelope(self.get_serializer(queryset, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return self._envelope(self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self._envelope(
            serializer.data,
            message=f"{self.resource_name} created successfully.",
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}
        return self._envelope(
            serializer.data, message=f"{self.resource_name} updated successfully."
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"success": True, "message": f"{self.resource_name} deleted successfully."},
            status=status.HTTP_200_OK,
        )
