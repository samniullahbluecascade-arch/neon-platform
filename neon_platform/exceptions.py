from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {"error": "Internal server error.", "detail": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Normalise all errors to {"error": "...", "detail": ...}
    if isinstance(response.data, dict) and "detail" in response.data:
        response.data = {"error": str(response.data["detail"])}
    elif isinstance(response.data, list):
        response.data = {"error": response.data[0] if response.data else "Unknown error"}
    else:
        response.data = {"error": response.data}

    return response
