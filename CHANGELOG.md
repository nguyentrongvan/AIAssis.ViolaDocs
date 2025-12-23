# Changelog

All notable changes to ViolaDocs will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-01-23

### Added
- **Text-to-Speech (TTS)**: Generate audio from document text with adjustable playback speed
  - Support for multiple languages (en, vi, ja, zh, ko, fr, de, es)
  - Speed control from 0.5x to 2.0x
  - Automatic chunking for long documents
  - Async processing via background workers
  - Frontend UI with audio player controls
  - API endpoints: `POST /documents/{doc_id}/tts/generate` and `GET /documents/{doc_id}/tts`
  
- **Language Detection**: Automatic language detection from document content
  - Detects primary language with confidence scores
  - Supports multiple languages (en, vi, ja, zh, ko, fr, de, es)
  - Automatically runs during OCR processing
  - Manual detection endpoint: `POST /documents/{doc_id}/detect-language`
  - Language metadata stored in document metadata
  - Frontend integration with language display

### Technical Details
- TTS uses Google Text-to-Speech (gTTS) provider
- Language detection uses langdetect library
- Both features integrated into document processing workflow
- Frontend UI includes TTS player controls and language display
- Settings API for TTS default speed and chunk size configuration

### Dependencies Added
- `langdetect>=1.0.9` - Language detection library
- `gtts>=2.5.0` - Google Text-to-Speech library
- `pydub>=0.25.1` - Audio processing for speed control and merging

## [1.1.0] - Previous version

### Features
- OCR Processing with Tesseract
- AI Document Intelligence (summarization, tagging, classification)
- Semantic Search with Qdrant
- AI Chatbot with RAG
- Workflow Management
- User Management with RBAC
- Device Integration
- Audit & Reports

## [1.0.0] - Initial Release

### Features
- Basic document management
- File upload and storage
- Folder organization
- User authentication
- Basic search functionality

