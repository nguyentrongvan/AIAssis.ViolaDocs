"""
AI Services Module
Contains all AI-related services: OCR, LLM, Embeddings

Note: Imports are lazy to avoid loading heavy dependencies (like PIL/Pillow for OCR)
when only embedding service is needed (e.g., in purge worker).
"""

# Lazy imports to avoid loading OCR dependencies when not needed
# This is important for purge worker which doesn't have PIL/Pillow installed

def _lazy_import_ocr():
    """Lazy import OCR service"""
    from .ocr_service import OcrService, get_ocr_service
    return OcrService, get_ocr_service

def _lazy_import_llm():
    """Lazy import LLM service"""
    from .llm_service import LLMService, get_llm_service
    return LLMService, get_llm_service

def _lazy_import_embedding():
    """Lazy import Embedding service"""
    from .embedding_service import EmbeddingService, get_embedding_service, EmbeddingModelUnavailableError
    return EmbeddingService, get_embedding_service, EmbeddingModelUnavailableError

# Provide direct imports for backward compatibility
# But these will only import when actually accessed
def __getattr__(name):
    """Lazy attribute access for services"""
    if name == "OcrService" or name == "get_ocr_service":
        OcrService, get_ocr_service = _lazy_import_ocr()
        if name == "OcrService":
            return OcrService
        return get_ocr_service
    elif name == "LLMService" or name == "get_llm_service":
        LLMService, get_llm_service = _lazy_import_llm()
        if name == "LLMService":
            return LLMService
        return get_llm_service
    elif name in ("EmbeddingService", "get_embedding_service", "EmbeddingModelUnavailableError"):
        EmbeddingService, get_embedding_service, EmbeddingModelUnavailableError = _lazy_import_embedding()
        if name == "EmbeddingService":
            return EmbeddingService
        elif name == "get_embedding_service":
            return get_embedding_service
        return EmbeddingModelUnavailableError
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "OcrService",
    "get_ocr_service",
    "LLMService",
    "get_llm_service",
    "EmbeddingService",
    "get_embedding_service",
    "EmbeddingModelUnavailableError",
]






