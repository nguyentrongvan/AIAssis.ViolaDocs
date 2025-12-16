from typing import Optional, List
import io
from PIL import Image
import fitz  # PyMuPDF

from ...config import settings, get_ocr_provider_from_db, get_ocr_languages_from_db
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
            # Map language codes to PaddleOCR language names
            lang_map = {
                'en': 'en',
                'vi': 'ch',  # Vietnamese uses Chinese model which includes Vietnamese
                'zh': 'ch',  # Chinese Simplified
                'ja': 'japan',  # Japanese
                'ko': 'korean',  # Korean
            }
            
            # Priority order: ch (supports vi and zh), then japan, korean, en
            # PaddleOCR only supports single language string, not list
            # So we choose the highest priority language from configured languages
            priority_order = ['ch', 'japan', 'korean', 'en']
            
            # Find the first priority language that's in the configured languages
            selected_lang = 'en'  # Default
            for lang in settings.ocr_lang_list:
                if lang in lang_map:
                    paddle_lang = lang_map[lang]
                    # If we find 'ch' (which covers vi and zh), use it
                    if paddle_lang == 'ch':
                        selected_lang = 'ch'
                        break
                    # Otherwise, use the first match in priority order
                    elif paddle_lang in priority_order and selected_lang not in ['ch']:
                        if priority_order.index(paddle_lang) < priority_order.index(selected_lang):
                            selected_lang = paddle_lang
            
            self.ocr = PaddleOCR(use_angle_cls=True, lang=selected_lang)
            print(f"PaddleOCR initialized with language: {selected_lang} (from configured: {settings.ocr_lang_list})")
        except ImportError:
            self.ocr = None
            print("PaddleOCR not installed. Install with: pip install paddleocr")
    
    def process_image(self, image_data: bytes, languages: List[str]) -> dict:
        if not self.ocr:
            return {"text": "", "error": "PaddleOCR not available"}
        
        try:
            image = Image.open(io.BytesIO(image_data))
            # Convert PIL Image to numpy array (PaddleOCR requires numpy array)
            import numpy as np
            img_array = np.array(image)
            result = self.ocr.ocr(img_array, cls=True)
            
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
            return {"text": "", "error": "PaddleOCR not available", "pages": 0}
        
        try:
            # Use PyMuPDF to extract pages as images
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            page_count = len(pdf_document)
            all_text = []
            
            for page_num in range(page_count):
                page = pdf_document[page_num]
                # Render page to image with good resolution (300 DPI)
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                # Convert to PIL Image then numpy array (PaddleOCR requires numpy array)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                import numpy as np
                img_array = np.array(img)
                
                # Run OCR on the image (PaddleOCR requires numpy array)
                result = self.ocr.ocr(img_array, cls=True)
                
                text_lines = []
                if result and result[0]:
                    for line in result[0]:
                        if line and len(line) >= 2:
                            text_lines.append(line[1][0])
                all_text.extend(text_lines)
            
            pdf_document.close()
            
            full_text = "\n".join(all_text)
            return {
                "text": full_text,
                "lines": all_text,
                "provider": "paddle",
                "pages": page_count,
                "languages": languages
            }
        except Exception as e:
            return {"text": "", "error": str(e), "pages": 0}


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
                print(f"Tesseract not found in system: {e}")
                print("Install Tesseract: https://github.com/tesseract-ocr/tesseract")
                self.ocr = None
        except ImportError:
            print("pytesseract not installed. Install with: pip install pytesseract")
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


class EasyOcrProvider(OcrProvider):
    """EasyOCR implementation"""
    
    def __init__(self):
        self.reader = None
        self._init_reader()
    
    def _init_reader(self):
        """Initialize EasyOCR reader with multi-language support"""
        try:
            import easyocr
            # Map language codes to EasyOCR language names
            lang_map = {
                'en': 'en',
                'vi': 'vi',
                'zh': 'ch_sim',  # Chinese Simplified
                'ja': 'ja',  # Japanese
                'ko': 'ko',  # Korean
                'fr': 'fr',
                'de': 'de',
                'es': 'es'
            }
            
            # Convert configured languages to EasyOCR format
            easyocr_langs = []
            for lang in settings.ocr_lang_list:
                if lang in lang_map:
                    easyocr_lang = lang_map[lang]
                    if easyocr_lang not in easyocr_langs:
                        easyocr_langs.append(easyocr_lang)
            
            # If no valid languages found, default to English
            if not easyocr_langs:
                easyocr_langs = ['en']
            
            # EasyOCR supports multi-language by passing a list
            self.reader = easyocr.Reader(easyocr_langs, gpu=False)
            print(f"EasyOCR initialized with languages: {easyocr_langs} (from configured: {settings.ocr_lang_list})")
        except ImportError:
            print("easyocr not installed. Install with: pip install easyocr")
            self.reader = None
        except Exception as e:
            print(f"Failed to initialize EasyOCR: {e}")
            self.reader = None
    
    def _get_languages(self, languages: List[str]) -> List[str]:
        """Convert language list to EasyOCR format"""
        lang_map = {
            "en": "en",
            "vi": "vi",
            "zh": "ch_sim",
            "ja": "ja",
            "ko": "ko",
            "fr": "fr",
            "de": "de",
            "es": "es"
        }
        easyocr_langs = []
        for lang in languages:
            if lang in lang_map:
                easyocr_lang = lang_map[lang]
                if easyocr_lang not in easyocr_langs:
                    easyocr_langs.append(easyocr_lang)
        return easyocr_langs if easyocr_langs else ["en"]
    
    def process_image(self, image_data: bytes, languages: List[str]) -> dict:
        if not self.reader:
            return {"text": "", "error": "EasyOCR not available"}
        
        try:
            image = Image.open(io.BytesIO(image_data))
            # Convert PIL Image to numpy array for EasyOCR
            import numpy as np
            img_array = np.array(image)
            
            # Read text from image
            results = self.reader.readtext(img_array)
            
            text_lines = []
            for (bbox, text, confidence) in results:
                if text.strip():
                    text_lines.append(text.strip())
            
            full_text = "\n".join(text_lines)
            return {
                "text": full_text,
                "lines": text_lines,
                "provider": "easyocr",
                "languages": languages
            }
        except Exception as e:
            return {"text": "", "error": str(e), "provider": "easyocr"}
    
    def process_pdf(self, pdf_data: bytes, languages: List[str]) -> dict:
        if not self.reader:
            return {"text": "", "error": "EasyOCR not available", "pages": 0}
        
        try:
            # Use PyMuPDF to extract pages as images
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            all_text = []
            import numpy as np
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                # Render page to image with good resolution (300 DPI)
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                # Convert to PIL Image then numpy array
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img_array = np.array(img)
                
                # Run OCR on the image
                results = self.reader.readtext(img_array)
                text_lines = []
                for (bbox, text, confidence) in results:
                    if text.strip():
                        text_lines.append(text.strip())
                all_text.extend(text_lines)
            
            page_count = len(pdf_document)
            pdf_document.close()
            
            full_text = "\n".join(all_text)
            return {
                "text": full_text,
                "lines": all_text,
                "provider": "easyocr",
                "pages": page_count,
                "languages": languages
            }
        except Exception as e:
            return {"text": "", "error": str(e), "provider": "easyocr", "pages": 0}


class OcrService:
    """OCR Service with provider abstraction"""
    
    def __init__(self, provider: Optional[OcrProvider] = None):
        self.provider = provider or self._get_default_provider()
    
    def _get_default_provider(self) -> OcrProvider:
        """Get default OCR provider based on config with fallback chain"""
        provider_name = settings.ocr_provider.lower()
        
        # Try configured provider first
        if provider_name == "paddle":
            provider = PaddleOcrProvider()
            if provider.ocr is not None:
                return provider
        elif provider_name == "tesseract":
            provider = TesseractOcrProvider()
            if provider.ocr is not None:
                return provider
        elif provider_name == "easyocr":
            provider = EasyOcrProvider()
            if provider.reader is not None:
                return provider
        elif provider_name == "auto":
            # Auto mode: try providers in order of preference
            # PaddleOCR (best for Vietnamese) -> EasyOCR -> Tesseract
            providers_to_try = [
                ("paddle", PaddleOcrProvider),
                ("easyocr", EasyOcrProvider),
                ("tesseract", TesseractOcrProvider)
            ]
            
            for name, provider_class in providers_to_try:
                try:
                    provider = provider_class()
                    if (hasattr(provider, 'ocr') and provider.ocr is not None) or \
                       (hasattr(provider, 'reader') and provider.reader is not None):
                        print(f"Using OCR provider: {name}")
                        return provider
                except Exception as e:
                    print(f"Failed to initialize {name}: {e}")
                    continue
            
            # If all fail, return PaddleOCR (will show error when used)
            print("Warning: No OCR provider available, falling back to PaddleOCR")
            return PaddleOcrProvider()
        else:
            raise ValueError(f"Unknown OCR provider: {settings.ocr_provider}. Options: paddle, tesseract, easyocr, auto")
        
        # If configured provider failed, try fallback chain
        print(f"Warning: Configured OCR provider '{provider_name}' not available, trying fallback...")
        fallback_providers = [
            ("paddle", PaddleOcrProvider),
            ("easyocr", EasyOcrProvider),
            ("tesseract", TesseractOcrProvider)
        ]
        
        for name, provider_class in fallback_providers:
            if name == provider_name:
                continue  # Skip the one we already tried
            try:
                provider = provider_class()
                if (hasattr(provider, 'ocr') and provider.ocr is not None) or \
                   (hasattr(provider, 'reader') and provider.reader is not None):
                    print(f"Using fallback OCR provider: {name}")
                    return provider
            except Exception as e:
                print(f"Fallback provider {name} also failed: {e}")
                continue
        
        # Last resort: return PaddleOCR (will show error when used)
        print("Error: No OCR providers available")
        return PaddleOcrProvider()
    
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


