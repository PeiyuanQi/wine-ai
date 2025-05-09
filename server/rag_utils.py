import os
import openai
import jieba
import re
import logger

# --- Constants ---
KNOWLEDGE_DIR = "data"  # Default knowledge source path
MAX_CONTEXT_LINES = 120  # Used only by retrieve_context
MAX_TOTAL_CHARS = 1024000  # Limit total characters read by load_knowledge
API_TEMPERATURE = 0.7
MODEL_NAME = "deepseek-chat"

# --- Core Functions ---

def load_knowledge(path=KNOWLEDGE_DIR):
    """Loads knowledge. Returns (knowledge_string, is_single_file) or (None, False) on error."""
    if os.path.isdir(path):
        knowledge_base_list = []
        total_chars = 0
        logger.info(f"Scanning directory '{path}' for markdown (.md) files...")
        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                files = [f for f in files if not f.startswith('.')]
                for filename in files:
                    if filename.lower().endswith(".md"):
                        filepath = os.path.join(root, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if total_chars + len(content) > MAX_TOTAL_CHARS:
                                    logger.warning(f"Reached character limit ({MAX_TOTAL_CHARS}). Stopping loading.")
                                    knowledge = "\n\n---\n\n".join(knowledge_base_list)
                                    logger.info(f"Knowledge loaded from {len(knowledge_base_list)} files in '{path}'.")
                                    return knowledge, False
                                knowledge_base_list.append(f"# Source: {os.path.relpath(filepath, path)}\n\n{content}")
                                total_chars += len(content)
                        except Exception as e:
                            logger.warning(f"Error reading file {filepath}: {e}")
            if not knowledge_base_list:
                logger.warning(f"No markdown (.md) files found in directory {path}")
                return "", False
            knowledge = "\n\n---\n\n".join(knowledge_base_list)
            logger.info(f"Knowledge loaded successfully from {len(knowledge_base_list)} files in '{path}'.")
            return knowledge, False
        except Exception as e:
            logger.error(f"Error scanning directory {path}: {e}")
            return None, False
    elif os.path.isfile(path):
        allowed_extensions = (".md", ".txt")
        if path.lower().endswith(allowed_extensions):
            logger.info(f"Loading knowledge from single file: {path}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if len(content) > MAX_TOTAL_CHARS:
                        logger.warning(f"File content exceeds limit ({MAX_TOTAL_CHARS}). Truncating.")
                        content = content[:MAX_TOTAL_CHARS]
                    knowledge = f"# Source: {os.path.basename(path)}\n\n{content}"
                    logger.info(f"Knowledge loaded successfully from {path}.")
                    return knowledge, True
            except Exception as e:
                logger.error(f"Error reading file {path}: {e}")
                return None, False
        else:
            logger.error(f"Input file '{path}' not allowed ({allowed_extensions}).")
            return None, False
    else:
        logger.error(f"Knowledge path not found: '{path}'")
        return None, False

def retrieve_context(query, knowledge_str):
    """Retrieves relevant context snippets using both Chinese and English tokenization."""
    if knowledge_str is None: return []
    if not knowledge_str: return []
    try:
        query = query.strip()
        if not query: return []
        
        # Combined Chinese and English stopwords
        chinese_stop_words = set([
            '的', '了', '和', '是', '就', '都', '而', '及', '与', '这', '那', '有', '在',
            '中', '上', '下', '由', '为', '以', '到', '等', '让', '向', '又', '但', '如',
            '或', '所', '因', '于', '只', '从', '给', '被', '得', '地', '着', '把', '之'
        ])
        
        english_stop_words = set([
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 
            'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 
            'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 
            'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 
            'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 
            'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 
            'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 
            'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 
            'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 
            'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 
            'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 
            'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
        ])
        
        # Combine both stopword sets
        stop_words = chinese_stop_words.union(english_stop_words)
        
        # Use jieba to segment mixed text - jieba handles both Chinese and English
        query_tokens = list(jieba.cut(query.lower()))
        
        # Post-process tokens to handle mixed language better
        processed_tokens = []
        for token in query_tokens:
            # Skip empty tokens
            if not token.strip():
                continue
                
            # Skip pure punctuation
            if re.match(r'^\W+$', token):
                continue
                
            # Skip stopwords (from either language)
            if token in stop_words:
                continue
                
            # Add to processed tokens
            processed_tokens.append(token)
            
        query_words = set(processed_tokens)
        
        logger.debug(f"Tokenized query words: {query_words}")
        
        # Process the knowledge base
        lines = knowledge_str.splitlines()
        relevant_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped: 
                continue
            
            # Process line with same technique as query
            line_tokens = list(jieba.cut(line_stripped.lower()))
            processed_line_tokens = []
            
            for token in line_tokens:
                if not token.strip() or re.match(r'^\W+$', token):
                    continue
                processed_line_tokens.append(token)
                
            line_words = set(processed_line_tokens)
            
            # Check for overlap with query terms
            if query_words.intersection(line_words):
                relevant_lines.append(line)
                
    except Exception as e:
        logger.error(f"Failed during context retrieval: {e}")
        return []
        
    logger.info(f"Found {len(relevant_lines)} potentially relevant lines.")
    return relevant_lines[:MAX_CONTEXT_LINES]

def generate_answer(query, context_str, client, is_dry_run):
    """Generates an answer using OpenAI or performs a dry run."""
    if not client:
        logger.error("OpenAI client is not initialized. Cannot generate answer.")
        return "OpenAI client is not initialized. Cannot generate answer."

    model_name = MODEL_NAME
    temperature = API_TEMPERATURE
    messages = []

    if context_str:
        logger.info("Generating answer using retrieved context.")
        system_prompt = "You are a knowledgeable wine expert assistant. Please prioritize answering based on the provided context. If the context is relevant, mention that you're basing your answer on that context. If the context isn't relevant or insufficient to answer the question, use your own knowledge to provide the best possible answer. Respond in Chinese."
        user_prompt = f"""Wine context:
---
{context_str}
---

Question: {query}

Answer:"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    else:
        logger.info("No relevant context found. Generating answer using general knowledge.")
        system_prompt = "You are a knowledgeable wine expert assistant. Respond in Chinese."
        user_prompt = query
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    if is_dry_run:
        logger.info("DRY RUN MODE - API Call details:")
        logger.debug(f"  Model: {model_name}")
        logger.debug("  Messages:")
        for msg in messages:
            logger.debug(f"    Role: {msg['role']}")
            content_preview = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
            logger.debug(f"    Content: {content_preview}")
        logger.debug(f"  Temperature: {temperature}")
        return "[Server in dry-run mode - No API call made]"

    try:
        logger.info(f"Attempting to generate answer for query: '{query}' using Model {model_name}...")
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
        )
        logger.info("OpenAI API call successful.")
        return response.choices[0].message.content.strip()
    except openai.APIError as e:
        logger.error(f"OpenAI API Error: {e}")
        return f"Sorry, there was an API error while contacting OpenAI: {e}"
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return f"Sorry, an unexpected error occurred: {e}"

def rag_query(query, current_knowledge, current_is_single_file, client, is_dry_run):
    """Performs RAG. If is_single_file, uses full knowledge; otherwise filters context."""
    if current_knowledge is None:
        logger.error("Knowledge base not loaded.")
        return "Knowledge base not loaded."

    context_string = ""
    if current_is_single_file:
        logger.info("Using full knowledge from single file as context.")
        context_string = current_knowledge
    else:
        logger.info("Filtering knowledge from directory scan based on query.")
        relevant_lines = retrieve_context(query, current_knowledge)
        if relevant_lines:
            context_string = "\n".join(relevant_lines)

    # Pass client and is_dry_run flag to generate_answer
    answer = generate_answer(query, context_string, client, is_dry_run)
    return answer 