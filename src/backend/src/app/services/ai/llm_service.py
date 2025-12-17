from typing import List, Optional, Dict
import httpx
from ...config import settings
from ...prompts import (
    CHATBOT_SYSTEM_PROMPT,
    CHATBOT_CONTEXT_PROMPT,
    CHATBOT_NO_CONTEXT_PROMPT,
    CLASSIFY_DOCUMENT_PROMPT,
    SUMMARIZE_DOCUMENT_PROMPT,
    EXTRACT_ENTITIES_PROMPT,
    RAG_QA_PROMPT,
    COMPARE_DOCUMENTS_PROMPT,
)


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


class OllamaLLMProvider(LLMProvider):
    """Ollama LLM implementation using native API"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, model: str = "llama3.2"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.http_client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize HTTP client for Ollama native API"""
        try:
            self.http_client = httpx.Client(
                timeout=60.0,
                base_url=self.base_url
            )
        except Exception as e:
            print(f"Failed to initialize Ollama LLM HTTP client: {e}")
            self.http_client = None
    
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
        """Generate response and return token usage"""
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


class LLMService:
    """LLM Service with prompt management"""
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or self._get_default_provider()
    
    def _get_default_provider(self) -> Optional[LLMProvider]:
        """Get default LLM provider (Ollama only)"""
        if settings.ollama_base_url:
            try:
                return OllamaLLMProvider(
                    base_url=settings.ollama_base_url,
                    api_key=settings.ollama_api_key if settings.ollama_api_key else None,
                    model=settings.ollama_llm_model
                )
            except Exception as e:
                print(f"Failed to initialize Ollama provider: {e}")
        
        return None
    
    def chat(self, question: str, context: Optional[List[str]] = None) -> str:
        """Chat with context (RAG)"""
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
    
    def chat_with_usage(self, question: str, context: Optional[List[str]] = None) -> tuple[str, dict]:
        """Chat with context (RAG) and return token usage"""
        if not self.provider:
            return "LLM provider not configured", {"token_in": 0, "token_out": 0}
        
        if context:
            prompt = CHATBOT_CONTEXT_PROMPT.format(
                context="\n\n".join([f"Document {i+1}:\n{ctx}" for i, ctx in enumerate(context)]),
                question=question
            )
        else:
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






