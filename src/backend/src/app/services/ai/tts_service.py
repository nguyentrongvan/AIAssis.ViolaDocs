"""
TTS (Text-to-Speech) Service
Supports multiple TTS providers with speed control
"""
import logging
from typing import Optional, Dict, Any, List
from io import BytesIO
import tempfile
import os

logger = logging.getLogger(__name__)


class TTSProvider:
    """Base class for TTS providers"""
    
    def generate_audio(self, text: str, language: str, voice_id: Optional[str] = None, speed: float = 1.0) -> bytes:
        """
        Generate audio from text
        
        Args:
            text: Text to convert to speech
            language: Language code (en, vi, ja, zh, etc.)
            voice_id: Optional voice identifier
            speed: Speech speed (0.5-2.0, default 1.0)
            
        Returns:
            Audio bytes (MP3 format)
        """
        raise NotImplementedError
    
    def get_available_voices(self, language: str) -> List[Dict[str, Any]]:
        """
        Get available voices for a language
        
        Returns:
            List of voice dicts with id, name, language, gender, etc.
        """
        raise NotImplementedError


class gTTSProvider(TTSProvider):
    """Google Text-to-Speech provider (free, requires internet)"""
    
    def __init__(self):
        try:
            from gtts import gTTS
            self.gtts = gTTS
            self.available = True
        except ImportError:
            logger.warning("gTTS not installed. Install with: pip install gtts")
            self.gtts = None
            self.available = False
    
    def _map_language_code(self, language: str) -> str:
        """Map internal language codes to gTTS codes"""
        lang_map = {
            "en": "en",
            "vi": "vi",
            "ja": "ja",
            "zh": "zh-cn",  # gTTS uses zh-cn for Chinese
            "ko": "ko",
            "fr": "fr",
            "de": "de",
            "es": "es"
        }
        return lang_map.get(language, language)
    
    def generate_audio(self, text: str, language: str, voice_id: Optional[str] = None, speed: float = 1.0, chunk_size: Optional[int] = None) -> bytes:
        """
        Generate audio using gTTS with chunking support for long text
        
        Args:
            text: Text to convert to speech
            language: Language code
            voice_id: Optional voice identifier
            speed: Speech speed (0.5-2.0)
            chunk_size: Optional chunk size in characters (default from settings, or 1200)
        """
        if not self.available:
            raise ValueError("gTTS not available. Please install gtts package.")
        
        if not text or len(text.strip()) == 0:
            raise ValueError("Text cannot be empty")
        
        # Get chunk size from settings if not provided
        # Note: If chunk_size is None, caller should provide it from async context
        # This avoids async/await issues in sync context
        if chunk_size is None:
            logger.warning("TTS chunk_size not provided, using default 1200. Consider passing chunk_size from async context.")
            chunk_size = 1200
        
        # Ensure chunk size is within reasonable range (1000-1500)
        chunk_size = max(1000, min(1500, chunk_size))
        
        try:
            # Map language code
            gtts_lang = self._map_language_code(language)
            
            # Split text into chunks if too long
            text_chunks = self._split_text_into_chunks(text, chunk_size)
            
            if len(text_chunks) > 1:
                logger.info(f"Text is long ({len(text)} chars), splitting into {len(text_chunks)} chunks (chunk_size={chunk_size}) for TTS generation")
            
            # Generate audio for each chunk
            audio_chunks = []
            for i, chunk in enumerate(text_chunks):
                logger.debug(f"Generating TTS for chunk {i+1}/{len(text_chunks)} ({len(chunk)} chars)")
                try:
                    tts = self.gtts(text=chunk, lang=gtts_lang, slow=False)
                    
                    # Save to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                        tmp_path = tmp_file.name
                        tts.save(tmp_path)
                    
                    try:
                        # Read audio bytes
                        with open(tmp_path, 'rb') as f:
                            chunk_audio = f.read()
                        audio_chunks.append(chunk_audio)
                    finally:
                        # Clean up temp file
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                except Exception as e:
                    logger.error(f"Error generating TTS for chunk {i+1}: {e}", exc_info=True)
                    raise ValueError(f"Failed to generate TTS audio for chunk {i+1}: {str(e)}")
            
            # Merge all audio chunks
            if len(audio_chunks) > 1:
                logger.info(f"Merging {len(audio_chunks)} audio chunks")
                audio_bytes = self._merge_audio_chunks(audio_chunks)
            else:
                audio_bytes = audio_chunks[0]
            
            # Apply speed control if needed
            if speed != 1.0:
                audio_bytes = self._adjust_speed(audio_bytes, speed)
            
            return audio_bytes
                    
        except Exception as e:
            logger.error(f"gTTS error: {e}", exc_info=True)
            raise ValueError(f"Failed to generate TTS audio: {str(e)}")
    
    def _split_text_into_chunks(self, text: str, max_length: int) -> List[str]:
        """
        Split text into chunks, trying to break at sentence boundaries
        
        Args:
            text: Text to split
            max_length: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Try to split by sentences first
        import re
        sentences = re.split(r'([.!?。！？]\s+)', text)
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]  # Include punctuation
            
            # If adding this sentence would exceed limit, save current chunk
            if len(current_chunk) + len(sentence) > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
            
            # If single sentence is too long, split by words
            if len(sentence) > max_length:
                words = sentence.split()
                for word in words:
                    if len(current_chunk) + len(word) + 1 > max_length:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = ""
                    current_chunk += word + " "
            else:
                current_chunk += sentence
        
        # Add remaining chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _merge_audio_chunks(self, audio_chunks: List[bytes]) -> bytes:
        """Merge multiple audio chunks into one"""
        try:
            from pydub import AudioSegment
            
            merged_audio = None
            for chunk_bytes in audio_chunks:
                chunk_audio = AudioSegment.from_mp3(BytesIO(chunk_bytes))
                if merged_audio is None:
                    merged_audio = chunk_audio
                else:
                    merged_audio += chunk_audio  # Concatenate
            
            # Export merged audio to bytes
            buffer = BytesIO()
            merged_audio.export(buffer, format="mp3")
            return buffer.getvalue()
            
        except ImportError:
            logger.error("pydub not available for merging audio chunks")
            raise ValueError("pydub is required for merging long text TTS. Install with: pip install pydub")
        except Exception as e:
            logger.error(f"Error merging audio chunks: {e}", exc_info=True)
            raise ValueError(f"Failed to merge audio chunks: {str(e)}")
    
    def _adjust_speed(self, audio_bytes: bytes, speed: float) -> bytes:
        """Adjust audio speed using pydub"""
        try:
            from pydub import AudioSegment
            from pydub.effects import speedup
            
            # Load audio from bytes
            audio = AudioSegment.from_mp3(BytesIO(audio_bytes))
            
            # Adjust speed
            if speed > 1.0:
                # Speed up
                audio = speedup(audio, playback_speed=speed)
            elif speed < 1.0:
                # Slow down - use frame manipulation
                audio = audio._spawn(audio.raw_data, overrides={
                    "frame_rate": int(audio.frame_rate * speed)
                }).set_frame_rate(audio.frame_rate)
            
            # Export to bytes
            buffer = BytesIO()
            audio.export(buffer, format="mp3")
            return buffer.getvalue()
            
        except ImportError:
            logger.warning("pydub not available for speed control, returning original audio")
            return audio_bytes
        except Exception as e:
            logger.error(f"Error adjusting audio speed: {e}", exc_info=True)
            return audio_bytes
    
    def get_available_voices(self, language: str) -> List[Dict[str, Any]]:
        """Get available voices for gTTS (gTTS doesn't expose voice selection)"""
        # gTTS doesn't support voice selection, return default voice
        return [{
            "id": "default",
            "name": f"Default {language.upper()} Voice",
            "language": language,
            "provider": "gtts",
            "gender": "neutral"
        }]


class TTSService:
    """TTS Service with provider abstraction"""
    
    def __init__(self, provider: Optional[TTSProvider] = None):
        self.provider = provider or self._get_default_provider()
    
    def _get_default_provider(self) -> Optional[TTSProvider]:
        """Get default TTS provider (gTTS)"""
        try:
            provider = gTTSProvider()
            if provider.available:
                return provider
        except Exception as e:
            logger.error(f"Failed to initialize gTTS provider: {e}", exc_info=True)
        return None
    
    @staticmethod
    def _get_provider_by_name(provider_name: str) -> Optional[TTSProvider]:
        """Get TTS provider by name"""
        provider_name_lower = provider_name.lower()
        
        if provider_name_lower == "gtts":
            return gTTSProvider()
        else:
            logger.warning(f"Unknown TTS provider: {provider_name}")
            return None
    
    def generate_audio(self, text: str, language: str, voice_id: Optional[str] = None, speed: float = 1.0, provider_name: Optional[str] = None, chunk_size: Optional[int] = None) -> bytes:
        """
        Generate audio from text
        
        Args:
            text: Text to convert to speech
            language: Language code
            voice_id: Optional voice identifier
            speed: Speech speed (0.5-2.0)
            provider_name: Optional provider name (if None, uses default)
            chunk_size: Optional chunk size in characters for long text processing
            
        Returns:
            Audio bytes (MP3 format)
        """
        provider = self.provider
        if provider_name:
            provider = self._get_provider_by_name(provider_name)
            if not provider:
                raise ValueError(f"TTS provider '{provider_name}' not available")
        
        if not provider:
            raise ValueError("No TTS provider available")
        
        # Check if provider supports chunk_size parameter
        import inspect
        provider_sig = inspect.signature(provider.generate_audio)
        if 'chunk_size' in provider_sig.parameters:
            return provider.generate_audio(text, language, voice_id, speed, chunk_size)
        else:
            return provider.generate_audio(text, language, voice_id, speed)
    
    def get_available_voices(self, language: str, provider_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available voices for a language"""
        provider = self.provider
        if provider_name:
            provider = self._get_provider_by_name(provider_name)
            if not provider:
                return []
        
        if not provider:
            return []
        
        return provider.get_available_voices(language)


# Singleton instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> Optional[TTSService]:
    """Get TTS service instance"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service

