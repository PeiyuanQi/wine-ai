import os
import openai
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# --- Constants ---
KNOWLEDGE_DIR = "data"  # Default knowledge source path
MAX_CONTEXT_LINES = 120  # Used only by retrieve_context
MAX_TOTAL_CHARS = 1024000  # Limit total characters read by load_knowledge
API_TEMPERATURE = 0.7
MODEL_NAME = "deepseek-chat"

# Download NLTK resources (uncomment first time)
# nltk.download('punkt')
# nltk.download('stopwords')

# --- Core Functions ---

def load_knowledge(path=KNOWLEDGE_DIR):
    """Loads knowledge. Returns (knowledge_string, is_single_file) or (None, False) on error."""
    if os.path.isdir(path):
        knowledge_base_list = []
        total_chars = 0
        print(f"Scanning directory '{path}' for markdown (.md) files...")
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
                                    print(f"Warning: Reached character limit ({MAX_TOTAL_CHARS}). Stopping loading.")
                                    knowledge = "\n\n---\n\n".join(knowledge_base_list)
                                    print(f"Knowledge loaded from {len(knowledge_base_list)} files in '{path}'.")
                                    return knowledge, False
                                knowledge_base_list.append(f"# Source: {os.path.relpath(filepath, path)}\n\n{content}")
                                total_chars += len(content)
                        except Exception as e:
                            print(f"Warning: Error reading file {filepath}: {e}")
            if not knowledge_base_list:
                print(f"Warning: No markdown (.md) files found in directory {path}")
                return "", False
            knowledge = "\n\n---\n\n".join(knowledge_base_list)
            print(f"Knowledge loaded successfully from {len(knowledge_base_list)} files in '{path}'.")
            return knowledge, False
        except Exception as e:
            print(f"Error scanning directory {path}: {e}")
            return None, False
    elif os.path.isfile(path):
        allowed_extensions = (".md", ".txt")
        if path.lower().endswith(allowed_extensions):
            print(f"Loading knowledge from single file: {path}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if len(content) > MAX_TOTAL_CHARS:
                        print(f"Warning: File content exceeds limit ({MAX_TOTAL_CHARS}). Truncating.")
                        content = content[:MAX_TOTAL_CHARS]
                    knowledge = f"# Source: {os.path.basename(path)}\n\n{content}"
                    print(f"Knowledge loaded successfully from {path}.")
                    return knowledge, True
            except Exception as e:
                print(f"Error reading file {path}: {e}")
                return None, False
        else:
            print(f"Error: Input file '{path}' not allowed ({allowed_extensions}).")
            return None, False
    else:
        print(f"Error: Knowledge path not found: '{path}'")
        return None, False

def retrieve_context(query, knowledge_str):
    """Retrieves relevant context snippets using English NLP tokenization."""
    if knowledge_str is None: return []
    if not knowledge_str: return []
    try:
        query = query.strip()
        if not query: return []
        
        # Tokenize and remove stopwords from query
        query_tokens = word_tokenize(query.lower())
        stop_words = set(stopwords.words('english'))
        query_tokens = [w for w in query_tokens if w.isalnum() and w not in stop_words]
        query_words = set(query_tokens)
        
        print(f"[Debug] Tokenized query words: {query_words}")
        
        lines = knowledge_str.splitlines()
        relevant_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped: continue
            
            # Tokenize and clean line
            line_tokens = word_tokenize(line_stripped.lower())
            line_tokens = [w for w in line_tokens if w.isalnum()]
            line_words = set(line_tokens)
            
            # Check for overlap with query terms
            if query_words.intersection(line_words):
                relevant_lines.append(line)
                
    except Exception as e:
        print(f"[Error] Failed during context retrieval: {e}")
        return []
        
    print(f"[Debug] Found {len(relevant_lines)} potentially relevant lines.")
    return relevant_lines[:MAX_CONTEXT_LINES]

def generate_answer(query, context_str, client, is_dry_run):
    """Generates an answer using OpenAI or performs a dry run."""
    if not client:
        return "OpenAI client is not initialized. Cannot generate answer."

    model_name = MODEL_NAME
    temperature = API_TEMPERATURE
    messages = []

    if context_str:
        print("[Info] Generating answer using retrieved context.")
        system_prompt = "You are a knowledgeable wine expert assistant. Please prioritize answering based on the provided context. If the context is relevant, mention that you're basing your answer on that context. If the context isn't relevant or insufficient to answer the question, use your own knowledge to provide the best possible answer."
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
        print("[Info] No relevant context found. Generating answer using general knowledge.")
        system_prompt = "You are a knowledgeable wine expert assistant."
        user_prompt = query
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    if is_dry_run:
        print("\n-- DRY RUN MODE --")
        print("API Call would be:")
        print(f"  Model: {model_name}")
        print("  Messages:")
        for msg in messages:
            print(f"    Role: {msg['role']}")
            content_preview = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
            print(f"    Content: {content_preview}")
        print(f"  Temperature: {temperature}")
        print("-- END DRY RUN --")
        return "[Server in dry-run mode - No API call made]"

    try:
        print(f"\n[API] Attempting to generate answer for query: '{query}' using Model {model_name}...")
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
        )
        print("[API] OpenAI API call successful.")
        return response.choices[0].message.content.strip()
    except openai.APIError as e:
        print(f"OpenAI API Error: {e}")
        return f"Sorry, there was an API error while contacting OpenAI: {e}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return f"Sorry, an unexpected error occurred: {e}"

def rag_query(query, current_knowledge, current_is_single_file, client, is_dry_run):
    """Performs RAG. If is_single_file, uses full knowledge; otherwise filters context."""
    if current_knowledge is None:
        return "Knowledge base not loaded."

    context_string = ""
    if current_is_single_file:
        print("[Info] Using full knowledge from single file as context.")
        context_string = current_knowledge
    else:
        print("[Info] Filtering knowledge from directory scan based on query.")
        relevant_lines = retrieve_context(query, current_knowledge)
        if relevant_lines:
            context_string = "\n".join(relevant_lines)

    # Pass client and is_dry_run flag to generate_answer
    answer = generate_answer(query, context_string, client, is_dry_run)
    return answer 