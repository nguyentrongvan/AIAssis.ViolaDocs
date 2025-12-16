from typing import List, Optional
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
    """Ollama LLM implementation using OpenAI-compatible API"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, model: str = "llama3.2"):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client with Ollama base URL"""
        try:
            import openai
            try:
                # Try with explicit parameters
                self.client = openai.OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key or "ollama"
                )
            except TypeError as e:
                # Handle proxies error if it occurs
                if "proxies" in str(e):
                    try:
                        # Try without api_key
                        self.client = openai.OpenAI(base_url=self.base_url)
                    except Exception as e2:
                        print(f"Failed to initialize LLM client: {e2}")
                        self.client = None
                else:
                    print(f"Failed to initialize LLM client: {e}")
                    self.client = None
        except ImportError:
            print("openai not installed")
            self.client = None
        except Exception as e:
            print(f"Failed to initialize Ollama LLM client: {e}")
            self.client = None
    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.client:
            return "Ollama LLM provider not available. Please check configuration."
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def generate_response_with_usage(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, dict]:
        """Generate response and return token usage"""
        if not self.client:
            return "Ollama LLM provider not available. Please check configuration.", {"token_in": 0, "token_out": 0}
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
            # Extract token usage from response
            usage = response.usage
            token_in = usage.prompt_tokens if usage else 0
            token_out = usage.completion_tokens if usage else 0
            
            return response.choices[0].message.content, {"token_in": token_in, "token_out": token_out}
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






