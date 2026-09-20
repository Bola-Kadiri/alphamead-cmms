from rest_framework.response import Response
from rest_framework import status


class APIResponse:
    """
    Unified API Response utility for consistent response formatting.

    Mirrors procurement.api.response.APIResponse — each app keeps its own
    copy per this project's vertical-slice-per-module convention.
    """

    @staticmethod
    def success(data=None, message="Success", status_code=status.HTTP_200_OK):
        response_data = {
            "success": True,
            "message": message,
            "data": data if data is not None else {}
        }
        return Response(response_data, status=status_code)

    @staticmethod
    def error(message="An error occurred", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        response_data = {
            "success": False,
            "message": message,
            "errors": errors if errors else {}
        }
        return Response(response_data, status=status_code)
