from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """Page-number pagination with a client-adjustable, bounded page size."""

    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("success", True),
                    ("count", self.page.paginator.count),
                    ("total_pages", self.page.paginator.num_pages),
                    ("current_page", self.page.number),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )

    def get_paginated_response_schema(self, schema):
        """Describe the shape `get_paginated_response` actually returns.

        The inherited version documents DRF's default envelope, which would
        leave `success`, `total_pages` and `current_page` out of the OpenAPI
        schema. Any change above belongs here too.
        """
        page_query = self.page_query_param
        return {
            "type": "object",
            "required": ["success", "count", "total_pages", "current_page", "results"],
            "properties": {
                "success": {"type": "boolean", "example": True},
                "count": {"type": "integer", "example": 42,
                          "description": "Total rows across all pages."},
                "total_pages": {"type": "integer", "example": 3},
                "current_page": {"type": "integer", "example": 1},
                "next": {
                    "type": "string", "nullable": True, "format": "uri",
                    "example": f"http://api.example.org/accounts/?{page_query}=4",
                },
                "previous": {
                    "type": "string", "nullable": True, "format": "uri",
                    "example": f"http://api.example.org/accounts/?{page_query}=2",
                },
                "results": schema,
            },
        }
