#!/usr/bin/env python3
"""
Script to check embedding configuration and diagnose issues
"""
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.app.config import settings
from src.app.services.ai.embedding_service import EmbeddingService, OllamaEmbeddingProvider
import httpx


def check_ollama_connection():
    """Check if Ollama is running and accessible"""
    print("=" * 60)
    print("Checking Ollama Connection...")
    print("=" * 60)
    
    base_url = settings.ollama_base_url
    print(f"Ollama Base URL: {base_url}")
    
    try:
        # Try to connect to Ollama
        response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        if response.status_code == 200:
            print("✓ Ollama is running and accessible")
            models = response.json().get("models", [])
            print(f"  Available models: {len(models)}")
            if models:
                print("  Model names:")
                for model in models[:10]:  # Show first 10
                    name = model.get("name", "unknown")
                    print(f"    - {name}")
            return True
        else:
            print(f"✗ Ollama returned status code: {response.status_code}")
            return False
    except httpx.ConnectError:
        print(f"✗ Cannot connect to Ollama at {base_url}")
        print("  Please ensure Ollama is running:")
        print("    - Local: ollama serve")
        print("    - Docker: docker run -d -p 11434:11434 ollama/ollama")
        return False
    except Exception as e:
        print(f"✗ Error checking Ollama: {e}")
        return False


def check_embedding_model():
    """Check if the embedding model is available"""
    print("\n" + "=" * 60)
    print("Checking Embedding Model...")
    print("=" * 60)
    
    model_name = settings.ollama_embedding_model
    base_url = settings.ollama_base_url
    print(f"Expected Model: {model_name}")
    print(f"Base URL: {base_url}")
    
    try:
        provider = OllamaEmbeddingProvider(
            base_url=base_url,
            api_key=settings.ollama_api_key if settings.ollama_api_key else None,
            model=model_name
        )
        
        if provider.client is None:
            print("✗ Failed to initialize Ollama client")
            return False
        
        print("✓ Ollama client initialized")
        
        if provider.is_model_available():
            print(f"✓ Model '{model_name}' is available")
            print(f"  Embedding dimension: {provider.dimension}")
            return True
        else:
            print(f"✗ Model '{model_name}' is NOT available")
            print(f"\n  To fix this, run:")
            print(f"    ollama pull {model_name}")
            print(f"\n  Or if using Docker:")
            print(f"    docker exec -it viadocs_ollama ollama pull {model_name}")
            return False
            
    except Exception as e:
        print(f"✗ Error checking embedding model: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_embedding_service():
    """Check the embedding service"""
    print("\n" + "=" * 60)
    print("Checking Embedding Service...")
    print("=" * 60)
    
    try:
        service = EmbeddingService()
        
        if not service.embedder:
            print("✗ Embedding provider is not initialized")
            diagnostic = service.get_availability_diagnostic()
            print(f"\n  Diagnostic: {diagnostic}")
            return False
        
        print("✓ Embedding provider initialized")
        
        if service.is_available():
            print("✓ Embedding service is available and ready")
            if isinstance(service.embedder, OllamaEmbeddingProvider):
                print(f"  Provider: Ollama")
                print(f"  Model: {service.embedder.model}")
                print(f"  Base URL: {service.embedder.base_url}")
                print(f"  Dimension: {service.embedder.dimension}")
            
            # Test embedding generation
            try:
                test_embedding = service.generate_embedding("test")
                print(f"✓ Test embedding generated successfully (dimension: {len(test_embedding)})")
                return True
            except Exception as e:
                print(f"✗ Failed to generate test embedding: {e}")
                return False
        else:
            print("✗ Embedding service is not available")
            diagnostic = service.get_availability_diagnostic()
            print(f"\n  Diagnostic: {diagnostic}")
            return False
            
    except Exception as e:
        print(f"✗ Error checking embedding service: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main diagnostic function"""
    print("\n" + "=" * 60)
    print("Embedding Configuration Diagnostic Tool")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  OLLAMA_BASE_URL: {settings.ollama_base_url}")
    print(f"  OLLAMA_EMBEDDING_MODEL: {settings.ollama_embedding_model}")
    print(f"  OLLAMA_API_KEY: {'***' if settings.ollama_api_key else '(not set)'}")
    
    results = []
    
    # Check Ollama connection
    results.append(("Ollama Connection", check_ollama_connection()))
    
    # Check embedding model
    results.append(("Embedding Model", check_embedding_model()))
    
    # Check embedding service
    results.append(("Embedding Service", check_embedding_service()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✓ All checks passed! Embedding is configured correctly.")
        return 0
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  1. Start Ollama: ollama serve (or use Docker)")
        print(f"  2. Pull the model: ollama pull {settings.ollama_embedding_model}")
        print("  3. Verify Ollama is accessible at the configured base URL")
        return 1


if __name__ == "__main__":
    sys.exit(main())

