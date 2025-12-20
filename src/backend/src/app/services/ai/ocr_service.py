from typing import Optional, List
import io
import logging
from PIL import Image
import fitz  # PyMuPDF

from ...config import settings, get_ocr_provider_from_db, get_ocr_languages_from_db
from ...prompts import *

logger = logging.getLogger(__name__)


class OcrProvider:
    """Base class for OCR providers"""
    
    def process_image(self, image_data: bytes, languages: List[str]) -> dict:
        """Process image and return text"""
        raise NotImplementedError
    
    def process_pdf(self, pdf_data: bytes, languages: List[str]) -> dict:
        """Process PDF and return text"""
        raise NotImplementedError


class TesseractOcrProvider(OcrProvider):
    """Tesseract OCR implementation"""
    
    def __init__(self):
        self.ocr = None
        self._init_ocr()
    
    def _init_ocr(self):
        """Initialize Tesseract OCR"""
        try:
            import pytesseract
            # Check if Tesseract is installed
            try:
                pytesseract.get_tesseract_version()
                self.ocr = pytesseract
            except Exception as e:
                logger.warning(f"Tesseract not found in system: {e}")
                logger.warning("Install Tesseract: https://github.com/tesseract-ocr/tesseract")
                self.ocr = None
        except ImportError:
            logger.warning("pytesseract not installed. Install with: pip install pytesseract")
            self.ocr = None
    
    def _get_lang_code(self, languages: List[str]) -> str:
        """Convert language list to Tesseract lang code (supports multi-language with +)"""
        lang_map = {
            "en": "eng",
            "vi": "vie",
            "zh": "chi_sim",  # Chinese Simplified
            "ja": "jpn",  # Japanese
            "ko": "kor",  # Korean
            "fr": "fra",
            "de": "deu",
            "es": "spa"
        }
        codes = []
        for lang in languages:
            if lang in lang_map:
                tesseract_code = lang_map[lang]
                if tesseract_code not in codes:
                    codes.append(tesseract_code)
        # Tesseract supports multi-language by joining with +
        return "+".join(codes) if codes else "eng"
    
    def process_image(self, image_data: bytes, languages: List[str]) -> dict:
        if not self.ocr:
            return {"text": "", "error": "Tesseract OCR not available"}
        
        try:
            image = Image.open(io.BytesIO(image_data))
            lang_code = self._get_lang_code(languages)
            
            # Extract text using Tesseract
            text = self.ocr.image_to_string(image, lang=lang_code)
            text_lines = [line.strip() for line in text.split("\n") if line.strip()]
            
            return {
                "text": text,
                "lines": text_lines,
                "provider": "tesseract",
                "languages": languages
            }
        except Exception as e:
            return {"text": "", "error": str(e), "provider": "tesseract"}
    
    def process_pdf(self, pdf_data: bytes, languages: List[str]) -> dict:
        if not self.ocr:
            return {"text": "", "error": "Tesseract OCR not available", "pages": 0}
        
        try:
            # Use PyMuPDF to extract pages as images
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            all_text = []
            lang_code = self._get_lang_code(languages)
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                # Render page to image with good resolution (300 DPI)
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                # Convert to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Run OCR on the image
                text = self.ocr.image_to_string(img, lang=lang_code)
                text_lines = [line.strip() for line in text.split("\n") if line.strip()]
                all_text.extend(text_lines)
            
            page_count = len(pdf_document)
            pdf_document.close()
            
            full_text = "\n".join(all_text)
            return {
                "text": full_text,
                "lines": all_text,
                "provider": "tesseract",
                "pages": page_count,
                "languages": languages
            }
        except Exception as e:
            return {"text": "", "error": str(e), "provider": "tesseract", "pages": 0}


class OcrService:
    """OCR Service with provider abstraction"""
    
    def __init__(self, provider: Optional[OcrProvider] = None):
        self.provider = provider or self._get_default_provider()
    
    def _get_default_provider(self) -> OcrProvider:
        """Get default OCR provider - only Tesseract is supported"""
        provider = TesseractOcrProvider()
        if provider.ocr is not None:
            return provider
        else:
            raise ValueError("Tesseract OCR not available. Please install Tesseract OCR engine.")
    
    async def process_image_async(self, image_data: bytes, languages: Optional[List[str]] = None) -> dict:
        """Process image with OCR (async version that reads settings from DB)"""
        if not self.provider:
            return {"text": "", "error": "OCR provider not available"}
        if languages is None:
            languages = await get_ocr_languages_from_db()
        try:
            result = self.provider.process_image(image_data, languages)
            return result
        except Exception as e:
            return {"text": "", "error": str(e)}
    
    def process_image(self, image_data: bytes, languages: Optional[List[str]] = None) -> dict:
        """Process image with OCR"""
        if not self.provider:
            return {"text": "", "error": "OCR provider not available"}
        if languages is None:
            languages = settings.ocr_lang_list
        try:
            result = self.provider.process_image(image_data, languages)
            return result
        except Exception as e:
            return {"text": "", "error": str(e)}
    
    async def process_pdf_async(self, pdf_data: bytes, languages: Optional[List[str]] = None) -> dict:
        """Process PDF with OCR (async version that reads settings from DB)"""
        if not self.provider:
            return {"text": "", "error": "OCR provider not available"}
        if languages is None:
            languages = await get_ocr_languages_from_db()
        try:
            result = self.provider.process_pdf(pdf_data, languages)
            return result
        except Exception as e:
            return {"text": "", "error": str(e)}
    
    def process_pdf(self, pdf_data: bytes, languages: Optional[List[str]] = None) -> dict:
        """Process PDF with OCR"""
        if not self.provider:
            return {"text": "", "error": "OCR provider not available"}
        if languages is None:
            languages = settings.ocr_lang_list
        try:
            result = self.provider.process_pdf(pdf_data, languages)
            return result
        except Exception as e:
            return {"text": "", "error": str(e)}


def get_ocr_service() -> OcrService:
    """Factory to get OCR service"""
    return OcrService()


