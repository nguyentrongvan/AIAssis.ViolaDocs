"""
Text Chunking Utility for RAG
Splits text into chunks with token-based sizing and overlap support
"""
from typing import List, Dict, Optional
import logging
import tiktoken

logger = logging.getLogger(__name__)


class TextChunker:
    """Chunk text into smaller pieces based on token count with overlap support"""
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Initialize chunker with tokenizer encoding
        
        Args:
            encoding_name: Tiktoken encoding name (cl100k_base works for most models)
        """
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            # Fallback to cl100k_base if specified encoding not found
            logger.warning(f"Encoding {encoding_name} not found, using cl100k_base: {e}", exc_info=True)
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if not text:
            return 0
        return len(self.encoding.encode(text))
    
    def chunk_text(
        self, 
        text: str, 
        chunk_size: int, 
        overlap: int = 0
    ) -> List[Dict[str, any]]:
        """
        Split text into chunks based on token count
        
        Args:
            text: Text to chunk
            chunk_size: Target token count per chunk
            overlap: Number of tokens to overlap between chunks
            
        Returns:
            List of chunk dictionaries with:
            - text: The chunk text
            - start_pos: Character position where chunk starts
            - end_pos: Character position where chunk ends
            - chunk_index: Zero-based index of chunk
            - token_count: Number of tokens in chunk
        """
        if not text or not text.strip():
            return []
        
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")
        
        # If text is shorter than chunk_size, return single chunk
        total_tokens = self.count_tokens(text)
        if total_tokens <= chunk_size:
            return [{
                "text": text,
                "start_pos": 0,
                "end_pos": len(text),
                "chunk_index": 0,
                "token_count": total_tokens
            }]
        
        chunks = []
        chunk_index = 0
        
        # Encode entire text once for efficiency
        tokens = self.encoding.encode(text)
        total_token_count = len(tokens)
        
        token_start = 0
        
        while token_start < total_token_count:
            # Calculate token end for this chunk
            token_end = min(token_start + chunk_size, total_token_count)
            
            # Decode tokens to get chunk text
            chunk_tokens = tokens[token_start:token_end]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Find character positions by searching for chunk_text in original text
            # For first chunk, start from beginning
            if chunk_index == 0:
                start_char_pos = 0
            else:
                # For subsequent chunks with overlap, find the overlap point
                # We need to find where the overlap portion starts in the original text
                # The overlap is the last 'overlap' tokens of previous chunk
                if token_start > 0:
                    # Decode overlap tokens to find overlap text
                    overlap_tokens = tokens[token_start:token_start + min(overlap, token_end - token_start)]
                    if overlap_tokens:
                        overlap_text = self.encoding.decode(overlap_tokens)
                        # Find overlap_text in previous chunk's end position
                        if chunks:
                            prev_end = chunks[-1]["end_pos"]
                            # Search backwards from previous end for overlap
                            search_start = max(0, prev_end - len(overlap_text) * 2)
                            overlap_pos = text.find(overlap_text, search_start, prev_end + len(overlap_text))
                            if overlap_pos >= 0:
                                start_char_pos = overlap_pos
                            else:
                                # Fallback: use previous end position
                                start_char_pos = chunks[-1]["end_pos"] - len(overlap_text)
                                if start_char_pos < 0:
                                    start_char_pos = 0
                        else:
                            start_char_pos = 0
                    else:
                        start_char_pos = chunks[-1]["end_pos"] if chunks else 0
                else:
                    start_char_pos = 0
            
            # Find end position by searching for chunk_text starting from start_char_pos
            # Try to find chunk_text in original text
            search_start = max(0, start_char_pos - 50)
            search_end = min(len(text), start_char_pos + len(chunk_text) * 2)
            
            # Find chunk_text in the original text
            chunk_pos = text.find(chunk_text, search_start, search_end)
            if chunk_pos >= 0:
                end_char_pos = chunk_pos + len(chunk_text)
            else:
                # If exact match not found, use decoded text length as approximation
                end_char_pos = start_char_pos + len(chunk_text)
                if end_char_pos > len(text):
                    end_char_pos = len(text)
            
            # Extract actual text from character positions
            actual_chunk_text = text[start_char_pos:end_char_pos]
            
            # Verify token count matches (should be close)
            actual_token_count = self.count_tokens(actual_chunk_text)
            
            chunks.append({
                "text": actual_chunk_text,
                "start_pos": start_char_pos,
                "end_pos": end_char_pos,
                "chunk_index": chunk_index,
                "token_count": actual_token_count
            })
            
            # Move to next chunk with overlap
            if token_end >= total_token_count:
                break
            
            # Calculate next start position with overlap
            token_start = token_end - overlap
            chunk_index += 1
        
        return chunks


def get_default_chunker() -> TextChunker:
    """Get default text chunker instance"""
    return TextChunker()

