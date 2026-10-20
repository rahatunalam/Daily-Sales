from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Keep every error in one shape: {"detail": "...", "errors": {...}?}."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        return response
    if isinstance(data, list):
        response.data = {"detail": " ".join(str(x) for x in data)}
        return response
    first = next(iter(data.values()), "") if isinstance(data, dict) else ""
    if isinstance(first, list):
        first = first[0] if first else ""
    response.data = {"detail": str(first) or "Invalid request.", "errors": data}
    return response
