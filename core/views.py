from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """Pagination par défaut : 200 lignes, taille ajustable via ?page_size= (max 1000)."""

    page_size = 200
    page_size_query_param = "page_size"
    max_page_size = 1000


class ResultsOnlyPagination(PageNumberPagination):
    """
    Custom pagination class for Django REST framework that:
    1. Supports optional pagination via query parameters
    2. Returns only the results without pagination metadata
    3. Works with ListAPIView and ModelViewSet

    Usage:
        - No query params (/products): Returns all records
        - With query params (/products?page=1&page_size=5): Returns paginated results

    Query Parameters:
        - page: Page number (1-based indexing)
        - page_size: Number of items per page
    """

    # Default page size if not specified
    page_size = 10

    # Query param for page size
    page_size_query_param = "page_size"

    # Maximum page size to prevent abuse
    max_page_size = 100

    def get_paginated_response(self, data):
        """
        Override to return only the results without pagination metadata.

        Args:
            data: Serialized page of results

        Returns:
            Response: DRF Response object containing only the results
        """
        return Response(data)

    def paginate_queryset(self, queryset, request, view=None):
        """
        Override to make pagination optional based on query parameters.

        Args:
            queryset: Django queryset to paginate
            request: HTTP request object
            view: API view instance

        Returns:
            list: Page of results if pagination requested, otherwise all results
        """
        # Check if pagination is requested via query parameters
        if not request.query_params.get(
            self.page_query_param
        ) and not request.query_params.get(self.page_size_query_param):
            return None

        return super().paginate_queryset(queryset, request, view)
