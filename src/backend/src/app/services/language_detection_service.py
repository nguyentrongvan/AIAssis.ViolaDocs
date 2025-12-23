"""
Language Detection Service
Detects the primary language of text using langdetect library
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class LanguageDetectionService:
    """Service for detecting language from text"""
    
    @staticmethod
    def detect_language(text: str) -> Dict[str, Any]:
        """
        Detect the primary language of text
        
        Args:
            text: Text to analyze
            
        Returns:
            {
                "primary": "en",  # Primary language code
                "confidence": 0.95,  # Confidence score (0-1)
                "secondary": [["vi", 0.05], ["ja", 0.02]],  # Other detected languages with scores
                "detected_at": "2025-01-23T10:00:00Z"
            }
        """
        if not text or len(text.strip()) < 3:
            # Text too short for reliable detection
            return {
                "primary": "en",  # Default to English
                "confidence": 0.0,
                "secondary": [],
                "detected_at": datetime.utcnow().isoformat() + "Z"
            }
        
        try:
            import langdetect
            
            # Detect primary language
            primary_lang = langdetect.detect(text)
            
            # Get all detected languages with confidence scores
            detected_langs = langdetect.detect_langs(text)
            
            # Map langdetect codes to internal codes
            lang_map = {
                "vi": "vi",
                "en": "en",
                "ja": "ja",
                "zh-cn": "zh",  # Map zh-cn to zh
                "zh": "zh",
                "ko": "ko",
                "fr": "fr",
                "de": "de",
                "es": "es"
            }
            
            # Normalize primary language
            primary_lang_normalized = lang_map.get(primary_lang, primary_lang)
            if primary_lang_normalized != primary_lang:
                logger.debug(f"Mapped language code {primary_lang} to {primary_lang_normalized}")
            
            # Get confidence for primary language
            primary_confidence = 0.0
            secondary = []
            
            for lang_info in detected_langs:
                lang_code = lang_info.lang
                confidence = lang_info.prob
                
                # Normalize language code
                normalized_code = lang_map.get(lang_code, lang_code)
                
                if normalized_code == primary_lang_normalized:
                    primary_confidence = confidence
                else:
                    secondary.append([normalized_code, confidence])
            
            # If we didn't find primary in detected_langs (shouldn't happen), use first one
            if primary_confidence == 0.0 and detected_langs:
                primary_confidence = detected_langs[0].prob
            
            result = {
                "primary": primary_lang_normalized,
                "confidence": round(primary_confidence, 3),
                "secondary": [[lang, round(prob, 3)] for lang, prob in secondary],
                "detected_at": datetime.utcnow().isoformat() + "Z"
            }
            
            logger.debug(f"Detected language: {result['primary']} (confidence: {result['confidence']})")
            return result
            
        except Exception as e:
            logger.error(f"Error detecting language: {e}", exc_info=True)
            # Return default on error
            return {
                "primary": "en",
                "confidence": 0.0,
                "secondary": [],
                "detected_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e)
            }

