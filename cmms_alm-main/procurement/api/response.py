from rest_framework.response import Response
from rest_framework import status


class APIResponse:
    """
    Unified API Response utility for consistent response formatting
    """
    
    @staticmethod
    def success(data=None, message="Success", status_code=status.HTTP_200_OK):
        """
        Create a successful response
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            
        Returns:
            Response object with standardized format
        """
        response_data = {
            "success": True,
            "message": message,
            "data": data if data is not None else {}
        }
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error(message="An error occurred", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        """
        Create an error response
        
        Args:
            message: Error message
            errors: Dictionary of field errors
            status_code: HTTP status code
            
        Returns:
            Response object with standardized format
        """
        response_data = {
            "success": False,
            "message": message,
            "errors": errors if errors else {}
        }
        return Response(response_data, status=status_code)
    
    @staticmethod
    def created(data=None, message="Resource created successfully"):
        """
        Create a 201 Created response
        
        Args:
            data: Created resource data
            message: Success message
            
        Returns:
            Response object with 201 status
        """
        return APIResponse.success(data=data, message=message, status_code=status.HTTP_201_CREATED)
    
    @staticmethod
    def not_found(message="Resource not found"):
        """
        Create a 404 Not Found response
        
        Args:
            message: Error message
            
        Returns:
            Response object with 404 status
        """
        return APIResponse.error(message=message, status_code=status.HTTP_404_NOT_FOUND)
    
    @staticmethod
    def validation_error(errors, message="Validation failed"):
        """
        Create a 400 Bad Request response for validation errors
        
        Args:
            errors: Dictionary of validation errors
            message: Error message
            
        Returns:
            Response object with 400 status
        """
        return APIResponse.error(message=message, errors=errors, status_code=status.HTTP_400_BAD_REQUEST)
    
    @staticmethod
    def unauthorized(message="Unauthorized"):
        """
        Create a 401 Unauthorized response
        
        Args:
            message: Error message
            
        Returns:
            Response object with 401 status
        """
        return APIResponse.error(message=message, status_code=status.HTTP_401_UNAUTHORIZED)
    
    @staticmethod
    def forbidden(message="Forbidden"):
        """
        Create a 403 Forbidden response
        
        Args:
            message: Error message
            
        Returns:
            Response object with 403 status
        """
        return APIResponse.error(message=message, status_code=status.HTTP_403_FORBIDDEN)

