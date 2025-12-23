#!/usr/bin/env python
"""
Script to initialize Ollama models for ViolaDocs.
This script is called from backend_entrypoint.sh after Ollama service is ready.

It checks if default models exist and pulls them if missing:
- LLM model: qwen2.5:0.5b (or from OLLAMA_LLM_MODEL env var)
- Embedding model: nomic-embed-text:latest (or from OLLAMA_EMBEDDING_MODEL env var)
"""
import os
import sys
import time
import json
from pathlib import Path

# Add src to path
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

try:
    import httpx
except ImportError:
    print("⚠️  httpx not available, trying requests...")
    try:
        import requests
        httpx = None
    except ImportError:
        print("❌ Neither httpx nor requests available. Cannot pull Ollama models.")
        sys.exit(0)

from app.config import settings


def wait_for_ollama(base_url: str, max_retries: int = 30, retry_interval: int = 2) -> bool:
    """Wait for Ollama service to be ready"""
    print(f"Waiting for Ollama service at {base_url}...")
    
    for attempt in range(max_retries):
        try:
            if httpx:
                with httpx.Client(timeout=5.0) as client:
                    response = client.get(f"{base_url}/api/tags")
                    if response.status_code == 200:
                        print(f"✅ Ollama service is ready!")
                        return True
            else:
                response = requests.get(f"{base_url}/api/tags", timeout=5.0)
                if response.status_code == 200:
                    print(f"✅ Ollama service is ready!")
                    return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"   Ollama not ready yet (attempt {attempt + 1}/{max_retries})...")
                time.sleep(retry_interval)
            else:
                print(f"⚠️  Ollama service not available after {max_retries} attempts: {e}")
                return False
    
    return False


def list_ollama_models(base_url: str) -> list:
    """List all available Ollama models"""
    try:
        if httpx:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    return [model.get("name", "") for model in models]
        else:
            response = requests.get(f"{base_url}/api/tags", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                return [model.get("name", "") for model in models]
    except Exception as e:
        print(f"⚠️  Error listing Ollama models: {e}")
        return []
    
    return []


def model_exists(model_name: str, existing_models: list) -> bool:
    """Check if model exists in the list (handle version tags)"""
    # Exact match
    if model_name in existing_models:
        return True
    
    # Check if model name without tag matches (e.g., "qwen2.5" matches "qwen2.5:0.5b")
    model_base = model_name.split(":")[0]
    for existing in existing_models:
        if existing.startswith(model_base + ":"):
            return True
    
    return False


def pull_ollama_model(base_url: str, model_name: str) -> bool:
    """Pull an Ollama model and wait for completion"""
    print(f"📥 Pulling model: {model_name}...")
    print(f"   This may take several minutes depending on model size...")
    
    try:
        # Ollama pull API uses streaming, so we need longer timeout
        timeout = 1800.0  # 30 minutes timeout for large models
        
        if httpx:
            with httpx.Client(timeout=timeout) as client:
                # Make streaming request
                with client.stream(
                    "POST",
                    f"{base_url}/api/pull",
                    json={"name": model_name},
                    timeout=timeout
                ) as response:
                    if response.status_code != 200:
                        print(f"⚠️  Failed to pull model {model_name}: HTTP {response.status_code}")
                        return False
                    
                    # Parse streaming JSON response
                    last_status = None
                    last_digest = None
                    total_size = None
                    completed_size = None
                    
                    for line in response.iter_lines():
                        if not line.strip():
                            continue
                        
                        try:
                            data = json.loads(line)
                            status = data.get("status", "")
                            
                            # Update progress
                            if status != last_status:
                                if status == "pulling":
                                    print(f"   Status: Pulling manifest...")
                                elif status == "downloading":
                                    digest = data.get("digest", "")
                                    if digest and digest != last_digest:
                                        print(f"   Status: Downloading layer {digest[:12]}...")
                                        last_digest = digest
                                elif status == "verifying":
                                    print(f"   Status: Verifying...")
                                elif status == "success":
                                    print(f"   ✅ Model pulled successfully!")
                                    return True
                                elif status == "error":
                                    error_msg = data.get("error", "Unknown error")
                                    print(f"   ❌ Error: {error_msg}")
                                    return False
                                
                                last_status = status
                            
                            # Show download progress if available
                            if "total" in data and "completed" in data:
                                total = data.get("total", 0)
                                completed = data.get("completed", 0)
                                if total > 0:
                                    percent = (completed / total) * 100
                                    # Only print progress every 10% to avoid spam
                                    if total_size != total or completed_size != completed:
                                        if total_size != total:
                                            total_size = total
                                        completed_size = completed
                                        # Convert to MB
                                        total_mb = total / (1024 * 1024)
                                        completed_mb = completed / (1024 * 1024)
                                        print(f"   Progress: {percent:.1f}% ({completed_mb:.1f}MB / {total_mb:.1f}MB)")
                        
                        except json.JSONDecodeError:
                            # Skip invalid JSON lines
                            continue
                        except Exception as e:
                            # Continue on other errors
                            continue
                    
                    # If we get here, the stream ended without success
                    print(f"⚠️  Pull completed but status unclear. Checking if model exists...")
                    # Wait a moment for model to be registered
                    time.sleep(2)
                    return True
        else:
            # Fallback for requests library (non-streaming)
            print(f"   Note: Using requests library, progress updates may be limited...")
            response = requests.post(
                f"{base_url}/api/pull",
                json={"name": model_name},
                timeout=timeout,
                stream=True
            )
            if response.status_code != 200:
                print(f"⚠️  Failed to pull model {model_name}: HTTP {response.status_code}")
                return False
            
            # Try to parse streaming response with requests
            last_status = None
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line.decode('utf-8'))
                    status = data.get("status", "")
                    
                    if status != last_status:
                        if status == "pulling":
                            print(f"   Status: Pulling manifest...")
                        elif status == "downloading":
                            print(f"   Status: Downloading...")
                        elif status == "verifying":
                            print(f"   Status: Verifying...")
                        elif status == "success":
                            print(f"   ✅ Model pulled successfully!")
                            return True
                        elif status == "error":
                            error_msg = data.get("error", "Unknown error")
                            print(f"   ❌ Error: {error_msg}")
                            return False
                        
                        last_status = status
                except:
                    continue
            
            # Wait a moment and check
            time.sleep(2)
            return True
                
    except Exception as e:
        print(f"⚠️  Error pulling model {model_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def init_ollama_models():
    """Initialize Ollama models if they don't exist"""
    # Get Ollama base URL from environment or config
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", settings.ollama_base_url)
    
    # Get model names from environment or config
    llm_model = os.getenv("OLLAMA_LLM_MODEL", settings.ollama_llm_model)
    embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", settings.ollama_embedding_model)
    
    print("=" * 60)
    print("Initializing Ollama Models")
    print("=" * 60)
    print(f"Ollama URL: {ollama_base_url}")
    print(f"LLM Model: {llm_model}")
    print(f"Embedding Model: {embedding_model}")
    print()
    
    # Wait for Ollama to be ready
    if not wait_for_ollama(ollama_base_url):
        print("⚠️  Skipping model initialization - Ollama service not available")
        return False
    
    # List existing models
    print("Checking existing models...")
    existing_models = list_ollama_models(ollama_base_url)
    
    if existing_models:
        print(f"✅ Found {len(existing_models)} existing model(s):")
        for model in existing_models:
            print(f"   - {model}")
    else:
        print("ℹ️  No existing models found")
    
    print()
    
    # Check and pull LLM model
    models_pulled = []
    
    if not model_exists(llm_model, existing_models):
        print(f"📥 LLM model '{llm_model}' not found, pulling...")
        if pull_ollama_model(ollama_base_url, llm_model):
            models_pulled.append(llm_model)
        else:
            print(f"⚠️  Failed to pull LLM model '{llm_model}'")
    else:
        print(f"✅ LLM model '{llm_model}' already exists, skipping")
    
    # Check and pull embedding model
    if not model_exists(embedding_model, existing_models):
        print(f"📥 Embedding model '{embedding_model}' not found, pulling...")
        if pull_ollama_model(ollama_base_url, embedding_model):
            models_pulled.append(embedding_model)
        else:
            print(f"⚠️  Failed to pull embedding model '{embedding_model}'")
    else:
        print(f"✅ Embedding model '{embedding_model}' already exists, skipping")
    
    print()
    if models_pulled:
        print(f"✅ Successfully pulled {len(models_pulled)} model(s): {', '.join(models_pulled)}")
        print("   All models are ready to use.")
    else:
        print("✅ All required models are already available")
    
    return True


if __name__ == "__main__":
    try:
        success = init_ollama_models()
        # Don't exit with error code - we don't want to fail startup if model pull fails
        sys.exit(0)
    except Exception as e:
        print(f"⚠️  Error initializing Ollama models: {e}")
        import traceback
        traceback.print_exc()
        # Exit with success code to not fail startup
        sys.exit(0)

