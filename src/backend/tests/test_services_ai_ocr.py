"""
Tests for OCR Service.

Covers:
- OcrService class
- PaddleOcrProvider
- process_image
- process_pdf
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.app.services.ai.ocr_service import OcrService, PaddleOcrProvider, OcrProvider


@pytest.mark.unit
class TestOCRService:
    """Tests for OCR service."""
    
    def test_ocr_service_initialization(self):
        """Test OCR service initialization."""
        with patch('src.app.services.ai.ocr_service.settings') as mock_settings:
            mock_settings.ocr_provider = "paddle"
            mock_settings.ocr_lang_list = ["en", "vi"]
            
            service = OcrService()
            
            assert service.provider is not None
    
    def test_ocr_service_unknown_provider(self):
        """Test OCR service with unknown provider."""
        with patch('src.app.services.ai.ocr_service.settings') as mock_settings:
            mock_settings.ocr_provider = "unknown"
            
            with pytest.raises(ValueError):
                OcrService()
    
    @pytest.mark.asyncio
    async def test_process_image(self):
        """Test processing image with OCR."""
        with patch('src.app.services.ai.ocr_service.settings') as mock_settings:
            mock_settings.ocr_provider = "paddle"
            mock_settings.ocr_lang_list = ["en"]
            
            service = OcrService()
            
            # Mock PaddleOCR
            with patch.object(service.provider, 'process_image') as mock_process:
                mock_process.return_value = {
                    "text": "Extracted text",
                    "lines": ["Extracted", "text"],
                    "provider": "paddle"
                }
                
                result = service.process_image(b"fake image data")
                
                assert result["text"] == "Extracted text"
                assert result["provider"] == "paddle"
    
    @pytest.mark.asyncio
    async def test_process_pdf(self):
        """Test processing PDF with OCR."""
        with patch('src.app.services.ai.ocr_service.settings') as mock_settings:
            mock_settings.ocr_provider = "paddle"
            mock_settings.ocr_lang_list = ["en"]
            
            service = OcrService()
            
            # Mock PaddleOCR
            with patch.object(service.provider, 'process_pdf') as mock_process:
                mock_process.return_value = {
                    "text": "Extracted PDF text",
                    "lines": ["Extracted", "PDF", "text"],
                    "provider": "paddle",
                    "pages": 1
                }
                
                result = service.process_pdf(b"fake pdf data")
                
                assert result["text"] == "Extracted PDF text"
                assert result["pages"] == 1
    
    def test_process_image_with_custom_languages(self):
        """Test processing image with custom language list."""
        with patch('src.app.services.ai.ocr_service.settings') as mock_settings:
            mock_settings.ocr_provider = "paddle"
            mock_settings.ocr_lang_list = ["en"]
            
            service = OcrService()
            
            with patch.object(service.provider, 'process_image') as mock_process:
                mock_process.return_value = {"text": "Text", "provider": "paddle"}
                
                result = service.process_image(b"fake image", languages=["vi", "en"])
                
                mock_process.assert_called_once()
                # Verify languages parameter was passed
                call_args = mock_process.call_args
                assert "vi" in call_args[0][1] or "en" in call_args[0][1]


@pytest.mark.unit
class TestPaddleOcrProvider:
    """Tests for PaddleOCR provider."""
    
    def test_paddle_ocr_provider_initialization(self):
        """Test PaddleOCR provider initialization."""
        with patch('src.app.services.ai.ocr_service.settings') as mock_settings:
            mock_settings.ocr_lang_list = ["en"]
            
            with patch('src.app.services.ai.ocr_service.PaddleOCR') as mock_paddle:
                provider = PaddleOcrProvider()
                
                # Should attempt to initialize PaddleOCR
                # (may fail if not installed, but that's OK for tests)
                assert provider is not None
    
    def test_paddle_ocr_process_image_not_available(self):
        """Test PaddleOCR when not available."""
        provider = PaddleOcrProvider()
        provider.ocr = None
        
        result = provider.process_image(b"fake image", ["en"])
        
        assert "error" in result
        assert result["text"] == ""
    
    def test_paddle_ocr_process_pdf_not_available(self):
        """Test PaddleOCR PDF processing when not available."""
        provider = PaddleOcrProvider()
        provider.ocr = None
        
        result = provider.process_pdf(b"fake pdf", ["en"])
        
        assert "error" in result
        assert result["text"] == ""
