from typing import List, Optional, Dict
import httpx
import logging
from ...config import settings, get_ollama_base_url_from_db, get_ollama_llm_model_from_db
from ...prompts import (
    CHATBOT_SYSTEM_PROMPT,
    CHATBOT_CONTEXT_PROMPT,
    CHATBOT_NO_CONTEXT_PROMPT,
    CHATBOT_CONTEXT_WITH_HISTORY_PROMPT,
    CHATBOT_HISTORY_ONLY_PROMPT,
    CLASSIFY_DOCUMENT_PROMPT,
    SUMMARIZE_DOCUMENT_PROMPT,
    EXTRACT_ENTITIES_PROMPT,
    RAG_QA_PROMPT,
    COMPARE_DOCUMENTS_PROMPT,
    GENERATE_TAGS_PROMPT,
    GENERATE_TAG_FROM_FILENAME_PROMPT,
)
from ...services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class LLMProvider:
    """Base class for LLM providers"""
    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate response from prompt"""
        raise NotImplementedError
    
    def generate_response_with_usage(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, dict]:
        """
        Generate response from prompt and return token usage.
        Returns: (response_text, {"token_in": int, "token_out": int})
        Default implementation calls generate_response and returns 0 tokens.
        """
        response = self.generate_response(prompt, system_prompt)
        return response, {"token_in": 0, "token_out": 0}
    
    async def generate_response_with_usage_async(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, dict]:
        """
        Generate response from prompt and return token usage (async version).
        Returns: (response_text, {"token_in": int, "token_out": int})
        Default implementation calls async generate_response if available.
        """
        if hasattr(self, 'generate_response_async'):
            response = await self.generate_response_async(prompt, system_prompt)
        else:
            response = self.generate_response(prompt, system_prompt)
        return response, {"token_in": 0, "token_out": 0}


class OllamaLLMProvider(LLMProvider):
    """Ollama LLM implementation using native API with async support"""
    
    # Class-level cache for async clients per base_url
    _async_clients: Dict[str, httpx.AsyncClient] = {}
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model or settings.ollama_llm_model  # Fallback to config if not provided
        self.http_client = None  # Keep sync client for backward compatibility
        self._init_client()
    
    def _init_client(self):
        """Initialize synchronous HTTP client for backward compatibility"""
        try:
            self.http_client = httpx.Client(
                timeout=60.0,
                base_url=self.base_url
            )
        except Exception as e:
            logger.error(f"Failed to initialize Ollama LLM HTTP client: {e}", exc_info=True)
            self.http_client = None
    
    async def _get_async_client(self) -> Optional[httpx.AsyncClient]:
        """Get or create async HTTP client with connection pooling"""
        if self.base_url not in OllamaLLMProvider._async_clients:
            try:
                OllamaLLMProvider._async_clients[self.base_url] = httpx.AsyncClient(
                    timeout=30.0,  # Reduced timeout for faster responses
                    base_url=self.base_url,
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                    http2=True  # Enable HTTP/2 for better performance
                )
            except Exception as e:
                logger.error(f"Failed to initialize Ollama LLM async HTTP client: {e}", exc_info=True)
                return None
        return OllamaLLMProvider._async_clients[self.base_url]
    
    def _messages_to_prompt(self, messages: List[Dict], system_prompt: Optional[str] = None) -> str:
        """Convert OpenAI messages format to Ollama prompt string"""
        parts = []
        if system_prompt:
            parts.append(f"System: {system_prompt}")
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        return "\n\n".join(parts)
    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.http_client:
            return "Ollama LLM provider not available. Please check configuration."
        
        try:
            # Convert prompt and system_prompt to Ollama format
            prompt_text = prompt
            if system_prompt:
                prompt_text = f"System: {system_prompt}\n\nUser: {prompt}"
            
            # Call Ollama native API
            response = self.http_client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt_text,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                return f"Error generating response: HTTP {response.status_code} - {response.text}"
            
            data = response.json()
            return data.get("response", "")
        except httpx.RequestError as e:
            return f"Error connecting to Ollama: {str(e)}"
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def generate_response_with_usage(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, dict]:
        """Generate response and return token usage (synchronous, for backward compatibility)"""
        if not self.http_client:
            return "Ollama LLM provider not available. Please check configuration.", {"token_in": 0, "token_out": 0}
        
        try:
            # Convert prompt and system_prompt to Ollama format
            prompt_text = prompt
            if system_prompt:
                prompt_text = f"System: {system_prompt}\n\nUser: {prompt}"
            
            # Call Ollama native API
            response = self.http_client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt_text,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                return f"Error generating response: HTTP {response.status_code} - {response.text}", {"token_in": 0, "token_out": 0}
            
            data = response.json()
            response_text = data.get("response", "")
            
            # Extract token usage from Ollama response
            token_in = data.get("prompt_eval_count", 0)
            token_out = data.get("eval_count", 0)
            
            return response_text, {"token_in": token_in, "token_out": token_out}
        except httpx.RequestError as e:
            return f"Error connecting to Ollama: {str(e)}", {"token_in": 0, "token_out": 0}
        except Exception as e:
            return f"Error generating response: {str(e)}", {"token_in": 0, "token_out": 0}
    
    async def generate_response_with_usage_async(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, dict]:
        """Generate response and return token usage (async version)"""
        async_client = await self._get_async_client()
        if not async_client:
            return "Ollama LLM provider not available. Please check configuration.", {"token_in": 0, "token_out": 0}
        
        try:
            # Convert prompt and system_prompt to Ollama format
            prompt_text = prompt
            if system_prompt:
                prompt_text = f"System: {system_prompt}\n\nUser: {prompt}"
            
            # Call Ollama native API asynchronously
            response = await async_client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt_text,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                return f"Error generating response: HTTP {response.status_code} - {response.text}", {"token_in": 0, "token_out": 0}
            
            data = response.json()
            response_text = data.get("response", "")
            
            # Extract token usage from Ollama response
            token_in = data.get("prompt_eval_count", 0)
            token_out = data.get("eval_count", 0)
            
            return response_text, {"token_in": token_in, "token_out": token_out}
        except httpx.RequestError as e:
            return f"Error connecting to Ollama: {str(e)}", {"token_in": 0, "token_out": 0}
        except Exception as e:
            return f"Error generating response: {str(e)}", {"token_in": 0, "token_out": 0}


class LLMService:
    """LLM Service with prompt management"""
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or self._get_default_provider()
    
    def _get_default_provider(self) -> Optional[LLMProvider]:
        """Get default LLM provider (Ollama only)"""
        if settings.ollama_base_url:
            try:
                # Use config default model - will be updated from DB in async methods (like generate_tags_async)
                return OllamaLLMProvider(
                    base_url=settings.ollama_base_url,
                    api_key=settings.ollama_api_key if settings.ollama_api_key else None,
                    model=settings.ollama_llm_model
                )
            except Exception as e:
                logger.error(f"Failed to initialize Ollama provider: {e}", exc_info=True)
        
        return None
    
    async def _get_prompts(self):
        """Get prompts from settings with fallback to defaults"""
        try:
            system_prompt = await SettingsService.get_setting(
                "chatbot_system_prompt",
                default=CHATBOT_SYSTEM_PROMPT
            )
            context_prompt = await SettingsService.get_setting(
                "chatbot_context_prompt",
                default=CHATBOT_CONTEXT_PROMPT
            )
            no_context_prompt = await SettingsService.get_setting(
                "chatbot_no_context_prompt",
                default=CHATBOT_NO_CONTEXT_PROMPT
            )
            context_with_history_prompt = await SettingsService.get_setting(
                "chatbot_context_with_history_prompt",
                default=CHATBOT_CONTEXT_WITH_HISTORY_PROMPT
            )
            history_only_prompt = await SettingsService.get_setting(
                "chatbot_history_only_prompt",
                default=CHATBOT_HISTORY_ONLY_PROMPT
            )
            return system_prompt, context_prompt, no_context_prompt, context_with_history_prompt, history_only_prompt
        except Exception as e:
            # If settings service fails, use defaults
            logger.warning(f"Failed to load prompts from settings, using defaults: {e}", exc_info=True)
            return CHATBOT_SYSTEM_PROMPT, CHATBOT_CONTEXT_PROMPT, CHATBOT_NO_CONTEXT_PROMPT, CHATBOT_CONTEXT_WITH_HISTORY_PROMPT, CHATBOT_HISTORY_ONLY_PROMPT
    
    def chat(self, question: str, context: Optional[List[str]] = None) -> str:
        """Chat with context (RAG) - synchronous version uses defaults"""
        if not self.provider:
            return "LLM provider not configured"
        
        if context:
            prompt = CHATBOT_CONTEXT_PROMPT.format(
                context="\n\n".join([f"Document {i+1}:\n{ctx}" for i, ctx in enumerate(context)]),
                question=question
            )
        else:
            prompt = CHATBOT_NO_CONTEXT_PROMPT.format(question=question)
        
        return self.provider.generate_response(prompt, system_prompt=CHATBOT_SYSTEM_PROMPT)
    
    def _format_conversation_history(self, conversation_history: Optional[List[Dict[str, str]]]) -> str:
        """Format conversation history into a readable string"""
        if not conversation_history:
            return ""
        
        formatted_lines = []
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                formatted_lines.append(f"User: {content}")
            elif role == "assistant":
                formatted_lines.append(f"Assistant: {content}")
        
        return "\n".join(formatted_lines)
    
    async def chat_with_usage_async(
        self, 
        question: str, 
        context: Optional[List[str]] = None, 
        conversation_history: Optional[List[Dict[str, str]]] = None,
        session=None
    ) -> tuple[str, dict]:
        """Chat with context (RAG) and conversation history, return token usage - async version loads prompts from settings"""
        if not self.provider:
            return "LLM provider not configured", {"token_in": 0, "token_out": 0}
        
        # Load model and base_url from database settings
        if isinstance(self.provider, OllamaLLMProvider):
            try:
                db_base_url = await get_ollama_base_url_from_db()
                db_model = await get_ollama_llm_model_from_db()
                
                # Update provider if model or base_url changed
                if db_model != self.provider.model or db_base_url != self.provider.base_url:
                    # Update model and base_url
                    self.provider.model = db_model
                    old_base_url = self.provider.base_url
                    self.provider.base_url = db_base_url.rstrip('/')
                    
                    # Recreate async client if base_url changed
                    if old_base_url != self.provider.base_url:
                        # Close old client if exists
                        if old_base_url in OllamaLLMProvider._async_clients:
                            try:
                                await OllamaLLMProvider._async_clients[old_base_url].aclose()
                            except:
                                pass
                            del OllamaLLMProvider._async_clients[old_base_url]
            except Exception as e:
                logger.warning(f"Failed to load LLM settings from DB, using current provider settings: {e}", exc_info=True)
        
        # Load prompts from settings
        system_prompt, context_prompt, no_context_prompt, context_with_history_prompt, history_only_prompt = await self._get_prompts()
        
        # Format conversation history if provided
        history_text = self._format_conversation_history(conversation_history) if conversation_history else ""
        
        # Choose appropriate prompt based on available context
        if history_text and context:
            # Both conversation history and document context
            prompt = context_with_history_prompt.format(
                conversation_history=history_text,
                context="\n\n".join([f"Document {i+1}:\n{ctx}" for i, ctx in enumerate(context)]),
                question=question
            )
        elif history_text:
            # Only conversation history, no document context
            prompt = history_only_prompt.format(
                conversation_history=history_text,
                question=question
            )
        elif context:
            # Only document context, no conversation history
            prompt = context_prompt.format(
                context="\n\n".join([f"Document {i+1}:\n{ctx}" for i, ctx in enumerate(context)]),
                question=question
            )
        else:
            # No context at all
            prompt = no_context_prompt.format(question=question)
        
        # Use async version if available, otherwise fall back to sync
        if hasattr(self.provider, 'generate_response_with_usage_async'):
            return await self.provider.generate_response_with_usage_async(prompt, system_prompt=system_prompt)
        else:
            return self.provider.generate_response_with_usage(prompt, system_prompt=system_prompt)
    
    def chat_with_usage(
        self, 
        question: str, 
        context: Optional[List[str]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> tuple[str, dict]:
        """Chat with context (RAG) and conversation history, return token usage - synchronous version uses defaults"""
        if not self.provider:
            return "LLM provider not configured", {"token_in": 0, "token_out": 0}
        
        # Format conversation history if provided
        history_text = self._format_conversation_history(conversation_history) if conversation_history else ""
        
        # Choose appropriate prompt based on available context
        if history_text and context:
            # Both conversation history and document context
            prompt = CHATBOT_CONTEXT_WITH_HISTORY_PROMPT.format(
                conversation_history=history_text,
                context="\n\n".join([f"Document {i+1}:\n{ctx}" for i, ctx in enumerate(context)]),
                question=question
            )
        elif history_text:
            # Only conversation history, no document context
            prompt = CHATBOT_HISTORY_ONLY_PROMPT.format(
                conversation_history=history_text,
                question=question
            )
        elif context:
            # Only document context, no conversation history
            prompt = CHATBOT_CONTEXT_PROMPT.format(
                context="\n\n".join([f"Document {i+1}:\n{ctx}" for i, ctx in enumerate(context)]),
                question=question
            )
        else:
            # No context at all
            prompt = CHATBOT_NO_CONTEXT_PROMPT.format(question=question)
        
        return self.provider.generate_response_with_usage(prompt, system_prompt=CHATBOT_SYSTEM_PROMPT)
    
    def classify_document(self, content: str) -> str:
        """Classify document content"""
        if not self.provider:
            return "other"
        
        prompt = CLASSIFY_DOCUMENT_PROMPT.format(content=content)
        return self.provider.generate_response(prompt)
    
    def summarize_document(self, content: str) -> str:
        """Summarize document"""
        if not self.provider:
            return "Summary not available"
        
        prompt = SUMMARIZE_DOCUMENT_PROMPT.format(document_content=content)
        return self.provider.generate_response(prompt)
    
    def extract_entities(self, content: str) -> dict:
        """Extract entities from document"""
        if not self.provider:
            return {}
        
        prompt = EXTRACT_ENTITIES_PROMPT.format(content=content)
        response = self.provider.generate_response(prompt)
        # TODO: Parse JSON response
        return {}
    
    def rag_qa(self, question: str, excerpts: List[str]) -> str:
        """Question answering with RAG"""
        if not self.provider:
            return "Answer not available"
        
        prompt = RAG_QA_PROMPT.format(
            excerpts="\n\n".join(excerpts),
            question=question
        )
        return self.provider.generate_response(prompt)
    
    def compare_documents(self, version1_content: str, version2_content: str) -> str:
        """Compare two document versions"""
        if not self.provider:
            return "Comparison not available"
        
        prompt = COMPARE_DOCUMENTS_PROMPT.format(
            version1_content=version1_content,
            version2_content=version2_content
        )
        return self.provider.generate_response(prompt)
    
    async def generate_tags_async(
        self,
        content: str,
        max_tags: int = 3,
        max_length: int = 50,
        filename: Optional[str] = None,
        session=None
    ) -> List[str]:
        """
        Generate tags from document content using LLM.
        Returns list of tag names (without prefix).
        One tag will be generated from filename, the rest from content.
        """
        if not self.provider:
            return []
        
        # Load model from database settings (LLM settings for chat) before generating tags
        if isinstance(self.provider, OllamaLLMProvider) and session:
            try:
                db_model = await get_ollama_llm_model_from_db()
                if db_model and db_model != self.provider.model:
                    logger.debug(f"[LLM Service] Updating model from '{self.provider.model}' to '{db_model}' for tag generation")
                    self.provider.model = db_model
            except Exception as e:
                logger.warning(f"[LLM Service] Failed to load LLM model from DB, using current model '{self.provider.model}': {e}", exc_info=True)
        
        tags = []
        
        # Generate 1 tag from filename if provided using LLM to generalize
        if filename:
            try:
                # Use LLM to generalize filename into a meaningful tag
                prompt_template = GENERATE_TAG_FROM_FILENAME_PROMPT
                
                # Format prompt with filename
                prompt = prompt_template.format(
                    filename=filename,
                    max_length=max_length
                )
                
                # Call LLM async to generalize filename
                response_text, _ = await self.provider.generate_response_with_usage_async(
                    prompt,
                    system_prompt=None
                )
                
                # Check if response is an error message (starts with "Error")
                if response_text and response_text.strip().startswith("Error"):
                    logger.error(f"[LLM Service] LLM returned error for filename '{filename}': {response_text}")
                    raise Exception(f"LLM error: {response_text}")
                
                if response_text:
                    # Clean up the response: remove quotes, trim whitespace
                    filename_tag = response_text.strip().strip('"\'`.,;:!?').strip()
                    
                    # Remove common prefixes/phrases that LLM might add
                    unwanted_prefixes = [
                        "based on the filename",
                        "based on filename",
                        "tag:",
                        "tag is:",
                        "the tag is:",
                        "generalized tag:",
                        "extracted tag:",
                    ]
                    for prefix in unwanted_prefixes:
                        if filename_tag.lower().startswith(prefix.lower()):
                            filename_tag = filename_tag[len(prefix):].strip().strip(':"\'`.,;:!?').strip()
                    
                    # Extract first word/phrase if response contains multiple words (take first meaningful part)
                    # Split by common separators and take the first meaningful part
                    import re
                    # Remove any leading text like "Based on..." and take first word/phrase
                    parts = re.split(r'[:\n\r\t,;]', filename_tag)
                    if parts:
                        filename_tag = parts[0].strip().strip('"\'`.,;:!?').strip()
                    
                    # Remove any remaining explanatory text (keep only alphanumeric and hyphens)
                    # Extract only the tag part (word or hyphenated phrase)
                    tag_match = re.search(r'([a-z0-9]+(?:-[a-z0-9]+)*)', filename_tag.lower())
                    if tag_match:
                        filename_tag = tag_match.group(1)
                    
                    # Validate and truncate if needed
                    if filename_tag and len(filename_tag) > 0 and len(filename_tag) <= max_length * 2:  # Allow some buffer for processing
                        # Truncate if needed
                        if len(filename_tag) > max_length:
                            filename_tag = filename_tag[:max_length]
                        tags.append(filename_tag)
                        logger.debug(f"[LLM Service] Generated generalized tag from filename '{filename}': {filename_tag}")
                    else:
                        logger.warning(f"[LLM Service] LLM returned invalid tag from filename '{filename}': '{response_text}'")
                        # Fallback: try to extract a simple tag from filename
                        import re
                        name_without_ext = re.sub(r'\.[^.]*$', '', filename)
                        parts = re.split(r'[_\-\s\.]+', name_without_ext.lower())
                        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 2 and p.strip().isalpha()]
                        if parts:
                            fallback_tag = parts[0][:max_length]
                            tags.append(fallback_tag)
                            logger.debug(f"[LLM Service] Using fallback tag from filename '{filename}': {fallback_tag}")
                else:
                    logger.warning(f"[LLM Service] LLM returned no response for filename '{filename}'")
                    
            except Exception as e:
                logger.error(f"[LLM Service] Error generating tag from filename '{filename}': {e}", exc_info=True)
        
        # Generate remaining tags from content
        remaining_tags_count = max_tags - len(tags)
        if remaining_tags_count > 0 and content:
            try:
                # Load prompt from settings or use default
                prompt_template = await SettingsService.get_setting(
                    "auto_tag.prompt",
                    default=GENERATE_TAGS_PROMPT,
                    session=session
                )
                
                # Format prompt with content and settings
                prompt = prompt_template.format(
                    content=content,
                    max_tags=remaining_tags_count,
                    max_length=max_length
                )
                
                # Call LLM async
                response_text, _ = await self.provider.generate_response_with_usage_async(
                    prompt,
                    system_prompt=None
                )
                
                # Check if response is an error message (starts with "Error")
                if response_text and response_text.strip().startswith("Error"):
                    logger.error(f"[LLM Service] LLM returned error for content: {response_text}")
                    raise Exception(f"LLM error: {response_text}")
                
                if response_text:
                    # Parse response: split by comma, trim, filter empty
                    content_tags = []
                    for tag in response_text.split(','):
                        tag = tag.strip()
                        if tag:
                            # Skip error messages
                            if tag.startswith("Error"):
                                continue
                            # Remove any leading/trailing quotes or special characters
                            tag = tag.strip('"\'`.,;:!?')
                            if tag:
                                content_tags.append(tag)
                    
                    # Limit number of tags and add to list
                    tags.extend(content_tags[:remaining_tags_count])
                    logger.debug(f"[LLM Service] Generated {len(content_tags[:remaining_tags_count])} tags from content")
            
            except Exception as e:
                logger.error(f"[LLM Service] Error generating tags from content: {e}", exc_info=True)
        
        return tags
    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generic response generation"""
        if not self.provider:
            return "LLM provider not configured"
        return self.provider.generate_response(prompt, system_prompt)


def get_llm_service() -> Optional[LLMService]:
    """Factory to get LLM service"""
    service = LLMService()
    if service.provider:
        return service
    return None






