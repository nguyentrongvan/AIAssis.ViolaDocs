"""
Prompt templates for AI services
"""

# Chatbot prompts
CHATBOT_SYSTEM_PROMPT = """You are an intelligent document management assistant with expertise in analyzing, summarizing, and extracting insights from documents.

Your capabilities:
- Deep understanding of document content and context
- Ability to synthesize information from multiple sources
- Analytical thinking to answer complex questions
- Proactive in suggesting relevant follow-up questions or additional information
- Clear communication with appropriate citations

Your approach:
- Read and understand the full context before answering
- Provide thoughtful, well-reasoned responses
- Be concise but comprehensive when needed
- If information is incomplete, acknowledge limitations and suggest what additional documents might help
- Use natural, conversational language while maintaining professionalism
- When citing sources, be specific about which document contains the information

CRITICAL: Always respond in the SAME LANGUAGE as the user's question. If they ask in Vietnamese, respond in Vietnamese. If they ask in English, respond in English. Match their language naturally and fluently."""

CHATBOT_CONTEXT_PROMPT = """I have found relevant documents that may help answer your question. Please analyze them carefully.

=== DOCUMENT CONTEXT ===
{context}

=== USER QUESTION ===
{question}

=== YOUR TASK ===
1. Carefully read and understand the documents above
2. Identify the most relevant information that answers the question
3. Synthesize the information into a clear, helpful response
4. Cite specific documents when referencing information
5. If the documents don't fully answer the question, explain what information is present and what is missing
6. Consider if there are related insights or follow-up suggestions that would be helpful

Provide a thoughtful, well-structured answer based on the available context. Use the same language as the user's question."""

CHATBOT_NO_CONTEXT_PROMPT = """User question: {question}

No specific documents were provided for this question. 

Your task:
1. Provide a helpful, informative response based on general knowledge if appropriate
2. If the question requires specific document information, politely explain that you'll need documents to provide an accurate answer
3. Suggest what type of documents or information would be helpful to search for
4. If relevant, offer to help with document management tasks (search, organization, etc.)

Be helpful and conversational while being honest about limitations. Respond in the same language as the question."""

CHATBOT_CONTEXT_WITH_HISTORY_PROMPT = """=== CONVERSATION HISTORY ===
{conversation_history}

=== RELEVANT DOCUMENTS ===
{context}

=== CURRENT QUESTION ===
{question}

=== YOUR TASK ===
You are continuing an ongoing conversation. Analyze both the conversation history and the provided documents to give a contextually appropriate response.

Consider:
- What has been discussed before (maintain conversation continuity)
- What the user is asking now (may reference previous exchanges)
- How the documents relate to both the current and previous questions
- Whether this is a follow-up, clarification, or new topic

Provide a response that:
1. Acknowledges the conversation flow naturally
2. Uses information from documents when relevant
3. References previous exchanges if they inform the current answer
4. Is clear about what information comes from documents vs. previous conversation
5. Maintains the same language as the user throughout

Answer thoughtfully and conversationally."""

CHATBOT_HISTORY_ONLY_PROMPT = """=== CONVERSATION HISTORY ===
{conversation_history}

=== CURRENT QUESTION ===
{question}

=== YOUR TASK ===
Continue this conversation naturally based on the context established in previous exchanges.

Consider:
- The flow and topic of the conversation so far
- Any information or conclusions from previous exchanges
- Whether the user is asking for clarification, elaboration, or a new related question
- The relationship between the current question and what has been discussed

Provide a response that:
1. Feels like a natural continuation of the dialogue
2. References previous exchanges when relevant
3. Is helpful and directly addresses the current question
4. Acknowledges if more information (like specific documents) would be helpful
5. Maintains conversational coherence and context

Respond in the same language as the user, maintaining a helpful and intelligent conversation."""

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

# Document type classification for auto tagging
CLASSIFY_DOCUMENT_TYPE_PROMPT = """Analyze the document content below and classify it into a single document type.

Common document types include (but not limited to):
- invoice, receipt, bill, payment
- contract, agreement, legal_document
- report, analysis, summary
- official_document, certificate, license
- dispatch, shipping, delivery_note
- cv, resume, curriculum_vitae
- menu, price_list, catalog
- email, letter, correspondence
- form, application, registration
- presentation, slide, deck
- manual, guide, instruction
- specification, technical_doc, api_doc
- other

[REQUIREMENTS]
- Return ONLY the document type as a single word or phrase with underscores
- Use lowercase, no spaces (use underscores)
- Be specific: prefer "official_document" over "document", "shipping_note" over "note"
- Maximum 30 characters
- Return ONLY the type, no explanations

[DOCUMENT CONTENT]
{content}

Document type:"""

# Document summarization prompts
SUMMARIZE_DOCUMENT_PROMPT = """You are ViolaDocs AI Assistant. Generate a document summary.

STRICT OUTPUT FORMAT - Output ONLY the summary, nothing else:
- Start directly with what the document is about (e.g., "This document discusses...", "Tài liệu này trình bày về...", "本文書は...")
- NO greetings, NO "I agree", NO "Sure", NO explanations
- NO prefixes like "Summary:", "Tóm tắt:"
- MUST be a COMPLETE paragraph ending with a period, NOT cut off mid-sentence
- Maximum {max_length} characters

CONTENT REQUIREMENTS:
- What type of document is this? (report, guide, research paper, manual, etc.)
- What is the main topic/subject?
- What are the key points or conclusions?

LANGUAGE: Write in the SAME language as the document content.

Document:
{document_content}

Output:"""

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
GENERATE_TAGS_PROMPT = """You are a document classifier. Read the document content carefully and extract exactly {max_tags} tags that ACCURATELY represent what the document is ACTUALLY about.

[CRITICAL REQUIREMENTS]
1. READ THE CONTENT CAREFULLY - tags must match the actual document content
2. DO NOT use generic/common tags like "machine_learning", "neural_network" unless the document is ACTUALLY about those topics
3. DO NOT copy examples from this instruction - create tags based on the REAL content
4. Tags must be 2-{max_length} characters, using ONLY: letters (a-z), numbers (0-9), underscores (_)
5. Use underscores to connect words: "invoice_management" not "invoice management"
6. NO spaces, NO hyphens, NO special characters, NO explanatory text

[FORBIDDEN]
- Do NOT return tags unrelated to the document content
- Do NOT use placeholder/example tags
- Do NOT include instruction words in tags

[FORMAT]
Return ONLY comma-separated tags based on the ACTUAL document content below.

[DOCUMENT CONTENT]
{content}

Tags (based on actual content above):"""

# Filename to tag generalization prompt
GENERATE_TAG_FROM_FILENAME_PROMPT = """Extract a single generalized tag from this filename.

Filename: {filename}

Instructions:
- Remove file extension (.pdf, .docx, etc.)
- Extract the main document type or category (e.g., invoice, report, contract, receipt)
- Remove dates, version numbers, company names, and specific identifiers
- Use lowercase, single word or phrase with underscores "_" connecting words
- NO spaces - use underscores "_" to separate words if needed
- NO special characters - only letters, numbers, and underscores
- Maximum {max_length} characters
- Return ONLY the tag word/phrase, no explanations, no prefixes, no other text

Examples:
- "invoice_2024_01_15.pdf" -> "invoice"
- "report_q1_2024_final.docx" -> "report" or "quarterly_report"
- "contract_ABC_Company_v2.pdf" -> "contract"
- "receipt_store_12345.jpg" -> "receipt"
- "machine_learning_notes.pdf" -> "machine_learning" or "ml_notes"

Tag:"""






