import random
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


class GeminiLLMProvider(LLMProvider):
    """Google Gemini implementation with multiple key support"""
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.models = {}
        self._init_models()
    
    def _init_models(self):
        """Initialize models for all API keys"""
        try:
            import google.generativeai as genai
            for key in self.api_keys:
                try:
                    genai.configure(api_key=key)
                    self.models[key] = genai.GenerativeModel('gemini-pro')
                except Exception as e:
                    print(f"Failed to initialize Gemini with key: {e}")
        except ImportError:
            print("google-generativeai not installed")
    
    def _get_random_model(self):
        """Get a random model from available keys"""
        if not self.models:
            return None
        key = random.choice(list(self.models.keys()))
        return self.models[key]
    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        model = self._get_random_model()
        if not model:
            return "LLM provider not available. Please configure API key."
        
        try:
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            # Retry with another key if quota exceeded
            if "quota" in str(e).lower() or "429" in str(e):
                if len(self.models) > 1:
                    model = self._get_random_model()
                    if model:
                        try:
                            response = model.generate_content(full_prompt)
                            return response.text
                        except:
                            pass
            return f"Error generating response: {str(e)}"


class OpenAILLMProvider(LLMProvider):
    """OpenAI GPT implementation with multiple key support"""
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.clients = {}
        self._init_clients()
    
    def _init_clients(self):
        """Initialize clients for all API keys"""
        try:
            import openai
            for key in self.api_keys:
                try:
                    self.clients[key] = openai.OpenAI(api_key=key)
                except Exception as e:
                    print(f"Failed to initialize OpenAI with key: {e}")
        except ImportError:
            print("openai not installed")
    
    def _get_random_client(self):
        """Get a random client from available keys"""
        if not self.clients:
            return None
        key = random.choice(list(self.clients.keys()))
        return self.clients[key]
    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        client = self._get_random_client()
        if not client:
            return "LLM provider not available. Please configure API key."
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            # Retry with another key if quota exceeded
            if "quota" in str(e).lower() or "429" in str(e) or "rate limit" in str(e).lower():
                if len(self.clients) > 1:
                    client = self._get_random_client()
                    if client:
                        try:
                            response = client.chat.completions.create(
                                model="gpt-3.5-turbo",
                                messages=messages
                            )
                            return response.choices[0].message.content
                        except:
                            pass
            return f"Error generating response: {str(e)}"


class LLMService:
    """LLM Service with prompt management"""
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or self._get_default_provider()
    
    def _get_default_provider(self) -> Optional[LLMProvider]:
        """Get default LLM provider"""
        gemini_keys = settings.gemini_api_keys
        openai_keys = settings.openai_api_keys
        
        if gemini_keys:
            return GeminiLLMProvider(gemini_keys)
        elif openai_keys:
            return OpenAILLMProvider(openai_keys)
        else:
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



