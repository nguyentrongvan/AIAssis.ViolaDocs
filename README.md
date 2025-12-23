<div align="center">

![ViolaDocs Logo](docs/logo.png)

# ViolaDocs - Document Management System

**AI-Powered Document Intelligence**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Product Showcase](docs/preview/welcome.jpg)](docs/showcase.html)

**[🎨 View Interactive Showcase →](https://htmlpreview.github.io/?https://github.com/nguyentrongvan/AIAssis.ViolaDocs/blob/develop/docs/showcase.html)**

</div>

## 🚀 Transform Your Document Workflow

**ViolaDocs** is a next-generation AI-powered Document Management System that revolutionizes how organizations handle, search, and interact with their documents. Combining cutting-edge OCR technology, semantic search, and intelligent AI assistance, ViolaDocs transforms paper documents and digital files into searchable, intelligent knowledge assets.

### Why ViolaDocs?

✨ **Intelligent Document Processing** - Automatically extract text from images and PDFs using Tesseract OCR supporting multiple languages (en, vi, ja, ko, zh, fr, de, es)  
🔊 **Text-to-Speech (TTS)** - Convert document text to speech audio with adjustable playback speed (0.5x - 2.0x) using Google TTS  
🌐 **Language Detection** - Automatic language detection from document content with confidence scores  
🤖 **AI Document Intelligence** - Automatic document summarization, tagging, classification, and entity extraction powered by local LLM (Ollama)  
🔍 **Semantic Search** - Find documents by meaning, not just keywords, using hybrid vector (Qdrant) and keyword search  
💬 **AI-Powered Assistant** - Get instant answers from your document library with our RAG-powered chatbot  
📋 **Workflow Automation** - Streamline review and approval processes with built-in workflow management  
🔒 **Enterprise Security** - Role-based access control, comprehensive audit logging, and enterprise-grade security  
📱 **Device Integration** - Direct integration with printers and scanners for seamless document capture  
📊 **Advanced Analytics** - Comprehensive reporting and analytics to track document usage and workflows  
🌐 **Multi-language UI** - Full internationalization support for English, Vietnamese, Japanese, and Chinese

## 🎯 Key Features

### Core Capabilities

- **📄 Document Management**: Upload, version control, search, and organize documents with intuitive folder structures
- **👁️ OCR Processing**: Tesseract OCR support for multiple languages (English, Vietnamese, Japanese, Korean, Chinese, French, German, Spanish) with high accuracy
- **🔊 Text-to-Speech (TTS)**: 
  - Convert document text to speech audio
  - Adjustable playback speed (0.5x - 2.0x)
  - Support for multiple languages (en, vi, ja, zh, ko, fr, de, es)
  - Automatic language detection before TTS generation
  - Async processing for large documents
- **🌐 Language Detection**: 
  - Automatic language detection from document content
  - Confidence scores for detected languages
  - Integrated into OCR processing workflow
  - Manual detection available via API
  - Language metadata stored in document metadata
- **🤖 AI Document Intelligence**: 
  - Automatic document summarization after OCR and tagging (configurable max length)
  - Automatic tag generation from document content
  - Document classification and type detection
  - Entity extraction from documents
  - Document comparison and analysis
- **🔎 Semantic Search**: Hybrid keyword + vector search using Qdrant vector database that understands context and meaning
- **💬 AI Chatbot**: RAG-powered assistant with document group scoping for intelligent Q&A
- **⚙️ Workflow Management**: Review and approval workflows with customizable task assignments
- **👥 User Management**: Role-based access control (Admin/Staff/User) with granular permissions
- **🖨️ Device Integration**: Printer/scanner connector for direct scanning and document capture
- **📈 Audit & Reports**: Comprehensive logging, reporting, and analytics dashboard
- **🌐 Multi-language Support**: Full internationalization (i18n) for English, Vietnamese, Japanese, and Chinese

### See It In Action

Check out our [interactive showcase](docs/showcase.html) to see ViolaDocs features in action with screenshots and demonstrations.

## About This Project

This project serves as a **practice implementation** demonstrating modern development workflows using **Cursor AI** for code generation and assistance. It showcases how AI-assisted development can accelerate the creation of complex enterprise applications, from architecture design to full-stack implementation.

**ViolaDocs** is part of the **AIAssis ecosystem**, a collection of projects exploring the integration of AI technologies in software development and business applications.

- **Document Management**: Upload, version control, search, and organize documents
- **OCR Processing**: Tesseract OCR support for multiple languages (en, vi, ja, ko, zh, fr, de, es)
- **Text-to-Speech (TTS)**: Convert document text to speech with adjustable speed
- **Language Detection**: Automatic language detection from document content
- **AI Document Intelligence**: Automatic summarization, tagging, classification, entity extraction, and document comparison
- **Semantic Search**: Hybrid keyword + vector search using Qdrant
- **AI Chatbot**: RAG-powered assistant with document group scoping
- **Workflow Management**: Review and approval workflows
- **User Management**: Role-based access control (Admin/Staff/User)
- **Device Integration**: Printer/scanner connector for direct scanning
- **Audit & Reports**: Comprehensive logging and reporting

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL with pgvector extension
- **Object Storage**: MinIO (S3-compatible)
- **Cache & Queue**: Redis
- **Vector Database**: Qdrant (for semantic search embeddings)
- **OCR Engine**: Tesseract OCR (via pytesseract)
- **LLM & Embeddings**: Ollama (local LLM with OpenAI-compatible API)
  - Supports various models: Llama 3.2, Llama 3.1, Qwen2.5, Qwen3, Mistral, Gemma2, etc.
  - Embedding models: nomic-embed-text, etc.
- **TTS Engine**: Google Text-to-Speech (gTTS) with pydub for audio processing
- **Language Detection**: langdetect library for automatic language identification
- **Background Workers**: 
  - OCR Worker (for async OCR processing, tagging, summarization, TTS, language detection)
  - Purge Worker (for document retention and cleanup)
- **Other**: Alembic (migrations), SQLAlchemy (ORM), httpx (async HTTP)

### Frontend
- **Framework**: Vue 3 (Composition API)
- **Build Tool**: Vite
- **State Management**: Pinia
- **Routing**: Vue Router
- **HTTP Client**: Axios
- **Internationalization**: vue-i18n (supports en, vi, ja, zh)
- **Charts**: Chart.js + vue-chartjs
- **UI Components**: Custom components with Lucide icons
- **Styling**: CSS3 with modern design patterns

## 🚀 Quick Start

For detailed setup instructions, see [SETUP.md](SETUP.md)

**Quick overview:**
1. Start infrastructure: `docker-compose up -d`
2. Setup backend: Configure `.env`, run migrations, start server
3. Setup frontend: Install dependencies, start dev server
4. Create admin user via API

See [SETUP.md](SETUP.md) for complete installation guide.

> 💡 **New to ViolaDocs?** Check out our [interactive showcase](docs/showcase.html) to explore features before installation.

## Infrastructure Services

The system runs on Docker Compose with the following services:

- **PostgreSQL** (with pgvector): Main relational database
- **MinIO**: S3-compatible object storage for documents
- **Redis**: Caching and job queue management
- **Qdrant**: Vector database for semantic search embeddings
- **Ollama**: Local LLM server for AI features (summarization, tagging, chatbot, etc.)
- **Backend API**: FastAPI application
- **Frontend**: Vue 3 application (served via Nginx)
- **OCR Worker**: Background worker for OCR processing, tagging, and summarization
- **Purge Worker**: Background worker for document retention and cleanup

## Project Structure

```
AIAssis.ViolaDocs/
├── docker/                     # Docker configurations
│   ├── docker-compose.base.yml # Base infrastructure services
│   ├── dev/                    # Development environment
│   └── prod/                   # Production environment
├── docs/                       # Design documentation
│   ├── architecture/
│   ├── api/
│   ├── data/
│   ├── ui-ux/
│   └── extensibility/
├── src/
│   ├── backend/                # FastAPI backend
│   │   ├── src/app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── models/         # SQLAlchemy models
│   │   │   ├── routers/        # API routes
│   │   │   ├── services/       # Business logic (AI, OCR, embedding, etc.)
│   │   │   ├── workers/        # Background job workers
│   │   │   └── prompts.py      # LLM prompts
│   │   ├── migrations/         # Alembic migrations
│   │   └── tests/              # Backend tests
│   └── frontend/               # Vue 3 frontend
│       └── src/
│           ├── components/     # Vue components
│           ├── views/          # Page views
│           ├── store/          # Pinia stores
│           ├── services/       # API services
│           └── i18n/           # Internationalization
├── nginx/                      # Nginx configuration
└── scripts/                    # Deployment scripts
```

## Default Credentials

After first migration, create an admin user via API or database:

```python
# Example: Create admin user
POST /api/v1/users
{
  "name": "Admin",
  "email": "admin@example.com",
  "password": "admin123",
  "role": "admin"
}
```

## Development

### Running Tests
```bash
# Backend
cd src/backend
pytest

# Frontend
cd src/frontend
npm run test
```

### Database Migrations
```bash
cd src/backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## AI-Assisted Development

This project was developed using **Cursor AI**, demonstrating:
- AI-powered code generation and refactoring
- Architecture design assistance
- Documentation generation
- Test case creation
- Bug fixing and optimization

The development process showcases how modern AI tools can enhance developer productivity while maintaining code quality and best practices.

## Ecosystem

Part of the **AIAssis** ecosystem - exploring AI integration in software development.

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

**Copyright (c) 2024 nguyentrongvan**

The MIT License allows you to:
- ✅ Use the software commercially
- ✅ Modify the software
- ✅ Distribute the software
- ✅ Sublicense the software
- ✅ Private use

**Conditions:**
- 📋 Include the original copyright notice
- 📋 Include a copy of the MIT License

**Limitations:**
- ❌ No liability or warranty

For more information, visit [choosealicense.com/licenses/mit/](https://choosealicense.com/licenses/mit/)

