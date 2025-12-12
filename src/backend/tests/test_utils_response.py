"""
Tests for Response Utils.

Covers:
- success_response
- error_response
"""
import pytest
from fastapi.responses import JSONResponse

from src.app.utils.response import success_response, error_response


@pytest.mark.unit
class TestResponseUtils:
    """Tests for response utility functions."""
    
    def test_success_response_default(self):
        """Test success response with default parameters."""
        response = success_response({"key": "value"})
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        
        body = response.body.decode()
        assert "is_success" in body
        assert "true" in body.lower()
        assert "key" in body
        assert "value" in body
    
    def test_success_response_custom_message(self):
        """Test success response with custom message."""
        response = success_response({"id": 1}, message="Operation successful")
        
        assert response.status_code == 200
        body = response.body.decode()
        assert "Operation successful" in body
    
    def test_success_response_custom_status_code(self):
        """Test success response with custom status code."""
        response = success_response({"id": 1}, status_code=201)
        
        assert response.status_code == 201
    
    def test_success_response_no_data(self):
        """Test success response with no data."""
        response = success_response()
        
        assert response.status_code == 200
        body = response.body.decode()
        assert "is_success" in body
    
    def test_error_response_default(self):
        """Test error response with default parameters."""
        response = error_response("Something went wrong")
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        
        body = response.body.decode()
        assert "is_success" in body
        assert "false" in body.lower()
        assert "Something went wrong" in body
    
    def test_error_response_custom_status_code(self):
        """Test error response with custom status code."""
        response = error_response("Not found", status_code=404)
        
        assert response.status_code == 404
    
    def test_error_response_with_details(self):
        """Test error response with details."""
        details = {"field": "email", "reason": "invalid format"}
        response = error_response("Validation failed", details=details)
        
        assert response.status_code == 400
        body = response.body.decode()
        assert "Validation failed" in body
        assert "field" in body or "email" in body
    
    def test_error_response_unauthorized(self):
        """Test error response for unauthorized access."""
        response = error_response("Unauthorized", status_code=401)
        
        assert response.status_code == 401
        body = response.body.decode()
        assert "Unauthorized" in body
    
    def test_error_response_forbidden(self):
        """Test error response for forbidden access."""
        response = error_response("Forbidden", status_code=403)
        
        assert response.status_code == 403




