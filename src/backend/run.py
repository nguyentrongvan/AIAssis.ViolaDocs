#!/usr/bin/env python
"""
Run script for ViolaDocs backend API server.
This script ensures the correct Python path is set before starting the server.
"""
import sys
import os
from pathlib import Path

# Add src directory to Python path
backend_dir = Path(__file__).parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

if __name__ == "__main__":
    # Setup logging before importing app
    from app.utils.logging_config import setup_logging
    setup_logging()
    
    import uvicorn
    from app.main import app
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(src_dir)]
    )






