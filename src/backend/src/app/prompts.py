"""
Prompt templates for AI services
"""

# Chatbot prompts
CHATBOT_SYSTEM_PROMPT = """You are a helpful document management assistant. 
You help users find information in their documents and answer questions based on the provided context.
Always cite the source documents when providing answers.

IMPORTANT: Respond in the same language that the user is using. If the user asks in Vietnamese, respond in Vietnamese. If the user asks in English, respond in English. Match the user's language naturally."""

CHATBOT_CONTEXT_PROMPT = """Context from documents:
{context}

Question: {question}

Please answer based on the context above. If the information is not in the context, say so clearly.

IMPORTANT: Respond in the same language that the user used in their question. Match the user's language naturally."""

CHATBOT_NO_CONTEXT_PROMPT = """Question: {question}

Please provide a helpful answer. If you need information from documents, let the user know they should search for specific documents first.

IMPORTANT: Respond in the same language that the user used in their question. Match the user's language naturally."""

CHATBOT_CONTEXT_WITH_HISTORY_PROMPT = """Previous conversation:
{conversation_history}

Context from documents:
{context}

Current question: {question}

Please answer based on the context above and the previous conversation. Consider the conversation history to understand the context and provide a coherent response. If the information is not in the context, say so clearly.

IMPORTANT: Respond in the same language that the user used in their question. Match the user's language naturally."""

CHATBOT_HISTORY_ONLY_PROMPT = """Previous conversation:
{conversation_history}

Current question: {question}

Please answer based on the previous conversation context. Provide a helpful and coherent response that continues the conversation naturally.

IMPORTANT: Respond in the same language that the user used in their question. Match the user's language naturally."""

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

# Auto tag generation prompt
GENERATE_TAGS_PROMPT = """Act as a professional librarian and content classifier. Your goal is to analyze the provided document content and extract the most meaningful entities and themes for document organization.

[TASKS]
1. Synthesize the core subject matter.
2. Generate exactly {max_tags} tags that represent the main topics, entities, or categories.
3. Ensure each tag is concise (max {max_length} chars).

[CONSTRAINTS]
- Prioritize: Specificity over generic terms (e.g., "Convolutional Neural Networks" instead of just "Tech").
- Consistency: Use Title Case for all tags.
- Output Format: Return ONLY a single string of tags separated by commas. No intro, no numbering, no period at the end.

[DOCUMENT CONTENT]
{content}

[CRITICAL OUTPUT]
Return only the comma-separated tags here: <tag1>,<tag2>,<tag3>,...<tagN>

Tags:"""

# Filename to tag generalization prompt
GENERATE_TAG_FROM_FILENAME_PROMPT = """Extract a single generalized tag from this filename.

Filename: {filename}

Instructions:
- Remove file extension (.pdf, .docx, etc.)
- Extract the main document type or category (e.g., invoice, report, contract, receipt)
- Remove dates, version numbers, company names, and specific identifiers
- Use lowercase, single word or hyphenated phrase
- Maximum {max_length} characters
- Return ONLY the tag word/phrase, no explanations, no prefixes, no other text

Examples:
- "invoice_2024_01_15.pdf" -> "invoice"
- "report_q1_2024_final.docx" -> "report" or "quarterly-report"
- "contract_ABC_Company_v2.pdf" -> "contract"
- "receipt_store_12345.jpg" -> "receipt"

Tag:"""






