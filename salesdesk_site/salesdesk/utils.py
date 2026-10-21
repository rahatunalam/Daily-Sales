from decimal import Decimal, InvalidOperation
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import exception_handler

class Pagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500

def api_exception_handler(exc, context):
    """api.js shows only data.detail, so every error is sent as {"detail": "..."}."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if isinstance(data, dict):
        msg = data.get('detail')
        if msg is None:
            first = next(iter(data.values()), 'Request failed.')
            msg = first[0] if isinstance(first, (list, tuple)) and first else first
    elif isinstance(data, (list, tuple)) and data:
        msg = data[0]
    else:
        msg = data
    response.data = {'detail': str(msg)}
    return response

def dec(value, default='0'):
    try:
        return Decimal(str(value if value not in (None, '') else default))
    except InvalidOperation:
        raise ValidationError('Enter a valid amount.')