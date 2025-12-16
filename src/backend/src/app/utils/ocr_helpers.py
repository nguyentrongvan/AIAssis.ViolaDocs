"""Helper functions for OCR provider installation and troubleshooting"""
import platform
import os
import shutil
from typing import Optional, Dict, Any


def detect_tesseract_path() -> Optional[str]:
    """Try to find Tesseract executable in common paths"""
    system = platform.system().lower()
    
    if system == "windows":
        # Common Windows installation paths
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        # Also check PATH
        tesseract_cmd = shutil.which("tesseract")
        if tesseract_cmd:
            return tesseract_cmd
        
        for path in common_paths:
            if os.path.exists(path):
                return path
    else:
        # Linux/Mac - check PATH
        tesseract_cmd = shutil.which("tesseract")
        if tesseract_cmd:
            return tesseract_cmd
    
    return None


def get_tesseract_install_guide(os_type: Optional[str] = None) -> Dict[str, Any]:
    """Get platform-specific Tesseract installation guide"""
    if os_type is None:
        os_type = platform.system().lower()
    
    guides = {
        "windows": {
            "title": "Install Tesseract OCR on Windows",
            "steps": [
                {
                    "step": 1,
                    "title": "Download Tesseract Installer",
                    "description": "Download the Windows installer from the official repository",
                    "action": "Visit: https://github.com/UB-Mannheim/tesseract/wiki",
                    "command": None
                },
                {
                    "step": 2,
                    "title": "Run the Installer",
                    "description": "Run the downloaded .exe file and follow the installation wizard",
                    "action": "Double-click the installer and follow the prompts",
                    "command": None
                },
                {
                    "step": 3,
                    "title": "Add to PATH (if not automatic)",
                    "description": "Ensure Tesseract is in your system PATH. The installer usually does this automatically.",
                    "action": "Add Tesseract installation directory to PATH environment variable",
                    "command": "Default path: C:\\Program Files\\Tesseract-OCR"
                },
                {
                    "step": 4,
                    "title": "Verify Installation",
                    "description": "Open a new command prompt and verify Tesseract is installed",
                    "action": "Run the verification command",
                    "command": "tesseract --version"
                },
                {
                    "step": 5,
                    "title": "Restart Application",
                    "description": "Restart this application to detect the newly installed Tesseract",
                    "action": "Restart the backend server",
                    "command": None
                }
            ],
            "download_link": "https://github.com/UB-Mannheim/tesseract/wiki",
            "verify_command": "tesseract --version"
        },
        "linux": {
            "title": "Install Tesseract OCR on Linux",
            "steps": [
                {
                    "step": 1,
                    "title": "Update Package Manager",
                    "description": "Update your package manager",
                    "action": "Run the update command",
                    "command": "sudo apt-get update  # Ubuntu/Debian\n# OR\nsudo yum update  # CentOS/RHEL"
                },
                {
                    "step": 2,
                    "title": "Install Tesseract",
                    "description": "Install Tesseract using your package manager",
                    "action": "Run the install command",
                    "command": "sudo apt-get install tesseract-ocr  # Ubuntu/Debian\n# OR\nsudo yum install tesseract  # CentOS/RHEL"
                },
                {
                    "step": 3,
                    "title": "Install Language Data (Optional)",
                    "description": "Install additional language data for better recognition",
                    "action": "Install language packages",
                    "command": "sudo apt-get install tesseract-ocr-vie tesseract-ocr-jpn tesseract-ocr-kor  # Ubuntu/Debian"
                },
                {
                    "step": 4,
                    "title": "Verify Installation",
                    "description": "Verify Tesseract is installed correctly",
                    "action": "Run the verification command",
                    "command": "tesseract --version"
                }
            ],
            "download_link": None,
            "verify_command": "tesseract --version"
        },
        "darwin": {
            "title": "Install Tesseract OCR on macOS",
            "steps": [
                {
                    "step": 1,
                    "title": "Install Homebrew (if not installed)",
                    "description": "Homebrew is the recommended package manager for macOS",
                    "action": "Install Homebrew",
                    "command": '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                },
                {
                    "step": 2,
                    "title": "Install Tesseract",
                    "description": "Install Tesseract using Homebrew",
                    "action": "Run the install command",
                    "command": "brew install tesseract"
                },
                {
                    "step": 3,
                    "title": "Install Language Data (Optional)",
                    "description": "Install additional language data",
                    "action": "Install language packages",
                    "command": "brew install tesseract-lang"
                },
                {
                    "step": 4,
                    "title": "Verify Installation",
                    "description": "Verify Tesseract is installed correctly",
                    "action": "Run the verification command",
                    "command": "tesseract --version"
                }
            ],
            "download_link": None,
            "verify_command": "tesseract --version"
        }
    }
    
    return guides.get(os_type, guides["windows"])


def get_easyocr_fix_guide() -> Dict[str, Any]:
    """Get fix guide for EasyOCR torch DLL errors"""
    return {
        "title": "Fix EasyOCR Torch DLL Error",
        "description": "This error is commonly caused by PyTorch DLL issues on Windows. Follow these steps to fix it.",
        "can_auto_fix": True,
        "steps": [
            {
                "step": 1,
                "title": "Install Visual C++ Redistributable",
                "description": "PyTorch requires Microsoft Visual C++ Redistributable. Download and install the latest version.",
                "action": "Download from Microsoft",
                "command": "Visit: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist",
                "auto_fixable": False
            },
            {
                "step": 2,
                "title": "Reinstall PyTorch and EasyOCR",
                "description": "Uninstall and reinstall PyTorch and EasyOCR to fix DLL conflicts.",
                "action": "Run the reinstall commands",
                "command": "pip uninstall torch easyocr -y\npip install torch easyocr",
                "auto_fixable": True
            },
            {
                "step": 3,
                "title": "Verify Installation",
                "description": "Verify that EasyOCR can be imported without errors.",
                "action": "Test the import",
                "command": "python -c \"import easyocr; print('EasyOCR installed successfully')\"",
                "auto_fixable": False
            },
            {
                "step": 4,
                "title": "Restart Application",
                "description": "Restart this application to detect the fixed EasyOCR installation.",
                "action": "Restart the backend server",
                "command": None,
                "auto_fixable": False
            }
        ],
        "auto_fix_command": "pip uninstall torch easyocr -y && pip install torch easyocr"
    }


