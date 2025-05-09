from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """
    Универсальная пагинация: `?page=<n>&limit=<m>`.

    limit — элементов на страницу (по умолчанию — 6)
    """

    default_limit_item_query_param = "limit"
    default_limit_item = settings.DEFAULT_LIMIT_ITEM
