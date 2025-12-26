from typing import Optional, List, Dict, Any
import io
import logging
from PIL import Image, ImageEnhance, ImageFilter
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
    """Tesseract OCR implementation with enhanced preprocessing and filtering"""
    
    def __init__(self, confidence_threshold: int = 30, psm_mode: int = 6, min_text_length: int = 2):
        """
        Initialize Tesseract OCR provider
        
        Args:
            confidence_threshold: Minimum confidence score (0-100) for text to be included
            psm_mode: Page Segmentation Mode (PSM) for Tesseract
                     6 = Uniform text block (default)
                     11 = Sparse text
                     12 = Single text line
            min_text_length: Minimum length of text block to be included
        """
        self.ocr = None
        self.confidence_threshold = confidence_threshold
        self.psm_mode = psm_mode
        self.min_text_length = min_text_length
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
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy
        
        Steps:
        1. Convert to grayscale if needed
        2. Enhance contrast
        3. Reduce noise
        4. Resize if too small
        """
        try:
            # Convert to RGB if needed (for consistent processing)
            if image.mode != 'RGB' and image.mode != 'L':
                image = image.convert('RGB')
            
            # Convert to grayscale for better OCR results
            if image.mode == 'RGB':
                image = image.convert('L')
            
            # Enhance contrast using PIL's ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)  # Increase contrast by 50%
            
            # Reduce noise using median filter (removes salt-and-pepper noise)
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Resize if image is too small (less than 300 DPI equivalent)
            # Assume standard viewing distance, 300 DPI = ~118 pixels per cm
            # Minimum width/height should be at least 1000 pixels for good OCR
            width, height = image.size
            min_dimension = 1000
            
            if width < min_dimension or height < min_dimension:
                # Calculate scale factor to reach minimum dimension
                scale = max(min_dimension / width, min_dimension / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.debug(f"Resized image from {width}x{height} to {new_width}x{new_height}")
            
            return image
        except Exception as e:
            logger.warning(f"Error during image preprocessing: {e}. Using original image.")
            return image
    
    def _validate_text(self, text: str, confidence: float) -> bool:
        """
        Validate if text is meaningful and not gibberish
        
        Args:
            text: Text to validate
            confidence: Confidence score from OCR
            
        Returns:
            True if text should be kept, False if it should be filtered out
        """
        if not text or len(text.strip()) < self.min_text_length:
            return False
        
        # Filter out text with very low confidence
        if confidence < self.confidence_threshold:
            return False
        
        # Filter out text that's mostly special characters or numbers only
        # Allow some special chars but not excessive
        text_stripped = text.strip()
        if len(text_stripped) < self.min_text_length:
            return False
        
        # Check if text is mostly special characters (more than 70%)
        special_char_count = sum(1 for c in text_stripped if not c.isalnum() and not c.isspace())
        if len(text_stripped) > 0 and special_char_count / len(text_stripped) > 0.7:
            return False
        
        # Filter out patterns that look like random noise
        # Too many repeated characters (e.g., "aaaa", "1111")
        if len(text_stripped) >= 3:
            char_counts = {}
            for char in text_stripped:
                char_counts[char] = char_counts.get(char, 0) + 1
            max_repeat = max(char_counts.values()) if char_counts else 0
            # If one character repeats more than 60% of the time, likely noise
            if max_repeat / len(text_stripped) > 0.6:
                return False
        
        return True
    
    def _extract_text_with_confidence(self, image: Image.Image, lang_code: str) -> Dict[str, Any]:
        """
        Extract text using Tesseract with confidence scores and filtering
        
        Returns:
            Dictionary with text, lines, and metadata
        """
        try:
            import pytesseract
            
            # Configure Tesseract with PSM mode
            config = f'--psm {self.psm_mode}'
            
            # Get detailed data including confidence scores
            data = pytesseract.image_to_data(image, lang=lang_code, config=config, output_type=pytesseract.Output.DICT)
            
            # Group words by line number
            lines_dict = {}
            confidence_scores = []
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0.0
                level = data['level'][i]
                line_num = data['line_num'][i]
                
                # Only process word-level text (level 5)
                if level == 5 and text:
                    # Validate text before including
                    if self._validate_text(text, conf):
                        if line_num not in lines_dict:
                            lines_dict[line_num] = []
                        lines_dict[line_num].append(text)
                        confidence_scores.append(conf)
            
            # Combine words in each line
            filtered_lines = []
            for line_num in sorted(lines_dict.keys()):
                line_text = ' '.join(lines_dict[line_num])
                if line_text.strip():
                    filtered_lines.append(line_text.strip())
            
            # Fallback: if no filtered lines, try simpler approach with lower threshold
            if not filtered_lines:
                logger.debug("Confidence filtering produced no results, trying fallback with lower threshold")
                # Temporarily lower threshold for fallback
                original_threshold = self.confidence_threshold
                self.confidence_threshold = max(10, self.confidence_threshold - 20)
                
                try:
                    # Create new dict for fallback to avoid conflicts
                    fallback_lines_dict = {}
                    for i in range(len(data['text'])):
                        text = data['text'][i].strip()
                        conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0.0
                        level = data['level'][i]
                        line_num = data['line_num'][i]
                        
                        if level == 5 and text and self._validate_text(text, conf):
                            if line_num not in fallback_lines_dict:
                                fallback_lines_dict[line_num] = []
                            fallback_lines_dict[line_num].append(text)
                    
                    for line_num in sorted(fallback_lines_dict.keys()):
                        line_text = ' '.join(fallback_lines_dict[line_num])
                        if line_text.strip():
                            filtered_lines.append(line_text.strip())
                finally:
                    self.confidence_threshold = original_threshold
            
            # Final fallback: use image_to_string but with preprocessing
            if not filtered_lines:
                logger.debug("Using final fallback: image_to_string")
                text = pytesseract.image_to_string(image, lang=lang_code, config=config)
                filtered_lines = [line.strip() for line in text.split("\n") if line.strip()]
                # Still validate the lines
                validated_lines = []
                for line in filtered_lines:
                    if len(line.strip()) >= self.min_text_length:
                        validated_lines.append(line.strip())
                filtered_lines = validated_lines
            
            full_text = "\n".join(filtered_lines)
            
            return {
                "text": full_text,
                "lines": filtered_lines,
                "confidence_scores": confidence_scores
            }
        except Exception as e:
            logger.error(f"Error extracting text with confidence: {e}", exc_info=True)
            # Fallback to basic method
            try:
                import pytesseract
                config = f'--psm {self.psm_mode}'
                text = pytesseract.image_to_string(image, lang=lang_code, config=config)
                text_lines = [line.strip() for line in text.split("\n") if line.strip()]
                return {
                    "text": text,
                    "lines": text_lines,
                    "confidence_scores": []
                }
            except Exception as e2:
                raise e
    
    def process_image(self, image_data: bytes, languages: List[str]) -> dict:
        if not self.ocr:
            return {"text": "", "error": "Tesseract OCR not available"}
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Preprocess image for better OCR accuracy
            processed_image = self._preprocess_image(image)
            
            lang_code = self._get_lang_code(languages)
            
            # Extract text with confidence filtering
            result = self._extract_text_with_confidence(processed_image, lang_code)
            
            return {
                "text": result["text"],
                "lines": result["lines"],
                "provider": "tesseract",
                "languages": languages,
                "confidence_scores": result.get("confidence_scores", [])
            }
        except Exception as e:
            logger.error(f"Error processing image with OCR: {e}", exc_info=True)
            return {"text": "", "error": str(e), "provider": "tesseract"}
    
    def process_pdf(self, pdf_data: bytes, languages: List[str]) -> dict:
        if not self.ocr:
            return {"text": "", "error": "Tesseract OCR not available", "pages": 0}
        
        try:
            # Use PyMuPDF to extract pages as images
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            all_text = []
            all_lines = []
            lang_code = self._get_lang_code(languages)
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                # Render page to image with good resolution (300 DPI)
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                # Convert to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Preprocess image for better OCR accuracy
                processed_img = self._preprocess_image(img)
                
                # Extract text with confidence filtering
                result = self._extract_text_with_confidence(processed_img, lang_code)
                
                # Add page separator for multi-page documents
                if result["lines"]:
                    all_lines.extend(result["lines"])
                    if page_num < len(pdf_document) - 1:  # Not the last page
                        all_lines.append("")  # Empty line as page separator
            
            page_count = len(pdf_document)
            pdf_document.close()
            
            # Filter out empty lines and join
            filtered_lines = [line for line in all_lines if line.strip()]
            full_text = "\n".join(filtered_lines)
            
            return {
                "text": full_text,
                "lines": filtered_lines,
                "provider": "tesseract",
                "pages": page_count,
                "languages": languages
            }
        except Exception as e:
            logger.error(f"Error processing PDF with OCR: {e}", exc_info=True)
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


