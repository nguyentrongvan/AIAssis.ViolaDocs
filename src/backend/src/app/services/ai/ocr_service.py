from typing import Optional, List
import io
from PIL import Image
import pdf2image

from ...config import settings
from ...prompts import *


class OcrProvider:
    """Base class for OCR providers"""
    
    def process_image(self, image_data: bytes, languages: List[str]) -> dict:
        """Process image and return text"""
        raise NotImplementedError
    
    def process_pdf(self, pdf_data: bytes, languages: List[str]) -> dict:
        """Process PDF and return text"""
        raise NotImplementedError


class PaddleOcrProvider(OcrProvider):
    """PaddleOCR implementation"""
    
    def __init__(self):
        try:
            from paddleocr import PaddleOCR
            # Support multiple languages
            lang = 'en'
            if 'vi' in settings.ocr_lang_list:
                lang = 'ch'  # Chinese includes Vietnamese support
            elif len(settings.ocr_lang_list) > 0:
                lang = settings.ocr_lang_list[0]
            
            self.ocr = PaddleOCR(use_angle_cls=True, lang=lang)
        except ImportError:
            self.ocr = None
            print("PaddleOCR not installed. Install with: pip install paddleocr")
    
    def process_image(self, image_data: bytes, languages: List[str]) -> dict:
        if not self.ocr:
            return {"text": "", "error": "PaddleOCR not available"}
        
        try:
            image = Image.open(io.BytesIO(image_data))
            result = self.ocr.ocr(image, cls=True)
            
            text_lines = []
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        text_lines.append(line[1][0])
            
            full_text = "\n".join(text_lines)
            return {
                "text": full_text,
                "lines": text_lines,
                "provider": "paddle",
                "languages": languages
            }
        except Exception as e:
            return {"text": "", "error": str(e)}
    
    def process_pdf(self, pdf_data: bytes, languages: List[str]) -> dict:
        if not self.ocr:
            return {"text": "", "error": "PaddleOCR not available"}
        
        try:
            images = pdf2image.convert_from_bytes(pdf_data)
            all_text = []
            
            for img in images:
                result = self.ocr.ocr(img, cls=True)
                text_lines = []
                if result and result[0]:
                    for line in result[0]:
                        if line and len(line) >= 2:
                            text_lines.append(line[1][0])
                all_text.extend(text_lines)
            
            full_text = "\n".join(all_text)
            return {
                "text": full_text,
                "lines": all_text,
                "provider": "paddle",
                "pages": len(images),
                "languages": languages
            }
        except Exception as e:
            return {"text": "", "error": str(e)}


class OcrService:
    """OCR Service with provider abstraction"""
    
    def __init__(self, provider: Optional[OcrProvider] = None):
        self.provider = provider or self._get_default_provider()
    
    def _get_default_provider(self) -> OcrProvider:
        """Get default OCR provider based on config"""
        if settings.ocr_provider == "paddle":
            return PaddleOcrProvider()
        else:
            raise ValueError(f"Unknown OCR provider: {settings.ocr_provider}")
    
    def process_image(self, image_data: bytes, languages: Optional[List[str]] = None) -> dict:
        """Process image with OCR"""
        if languages is None:
            languages = settings.ocr_lang_list
        return self.provider.process_image(image_data, languages)
    
    def process_pdf(self, pdf_data: bytes, languages: Optional[List[str]] = None) -> dict:
        """Process PDF with OCR"""
        if languages is None:
            languages = settings.ocr_lang_list
        return self.provider.process_pdf(pdf_data, languages)


def get_ocr_service() -> OcrService:
    """Factory to get OCR service"""
    return OcrService()

