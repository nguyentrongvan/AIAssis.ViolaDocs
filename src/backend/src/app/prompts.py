"""
Prompt templates for AI services
"""

# Chatbot prompts
CHATBOT_SYSTEM_PROMPT = """You are a helpful document management assistant. 
You help users find information in their documents and answer questions based on the provided context.
Always cite the source documents when providing answers."""

CHATBOT_CONTEXT_PROMPT = """Context from documents:
{context}

Question: {question}

Please answer based on the context above. If the information is not in the context, say so clearly."""

CHATBOT_NO_CONTEXT_PROMPT = """Question: {question}

Please provide a helpful answer. If you need information from documents, let the user know they should search for specific documents first."""

# Document classification prompts
CLASSIFY_DOCUMENT_PROMPT = """Classify the following document content into one of these categories:
- invoice
- contract
- report
- letter
- form
- receipt
- other

Document content:
{content}

Return only the category name."""

# Document summarization prompts
SUMMARIZE_DOCUMENT_PROMPT = """Summarize the following document in 3-5 sentences:

{document_content}

Summary:"""

# Entity extraction prompts
EXTRACT_ENTITIES_PROMPT = """Extract key entities from the following document:
- Names
- Dates
- Amounts/Money
- Organizations
- Locations

Document content:
{content}

Return as JSON format with keys: names, dates, amounts, organizations, locations."""

# Question answering with RAG
RAG_QA_PROMPT = """Based on the following document excerpts, answer the question.

Document excerpts:
{excerpts}

Question: {question}

Answer:"""

# Document comparison prompts
COMPARE_DOCUMENTS_PROMPT = """Compare these two document versions and highlight the key differences:

Version 1:
{version1_content}

Version 2:
{version2_content}

Key differences:"""

# Translation prompts (if needed)
TRANSLATE_PROMPT = """Translate the following text from {source_lang} to {target_lang}:

{text}

Translation:"""


