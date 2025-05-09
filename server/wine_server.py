import os
from dotenv import load_dotenv
import openai
import argparse
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from rag_utils import load_knowledge, rag_query, KNOWLEDGE_DIR

# Load environment variables
load_dotenv()
llm_api_key = os.getenv("LLM_API_KEY")
api_base_url = "https://api.deepseek.com"

# --- Global Variables (initialized at startup) ---
client = None
knowledge_base = None
is_single_file_load = False
IS_DRY_RUN = False  # Global flag for dry-run mode

# --- Server Setup & Initialization ---
app = FastAPI(title="Wine-AI API", description="Wine knowledge retrieval API using OpenAI")

# Define request model
class QueryRequest(BaseModel):
    query: str

def initialize_app(dry_run_mode=False):
    global client, knowledge_base, is_single_file_load, IS_DRY_RUN
    IS_DRY_RUN = dry_run_mode
    print(f"Initializing Wine-AI RAG server... (Dry Run: {IS_DRY_RUN})")

    # Initialize OpenAI Client
    if llm_api_key:
        print("Attempting to initialize OpenAI client...")
        try:
            client = openai.OpenAI(
                api_key=llm_api_key,
                base_url=api_base_url
            )
            print("OpenAI client initialized successfully.")
        except Exception as e:
            print(f"Fatal: Error initializing OpenAI client: {e}")
            client = None
    else:
        print("Fatal: LLM_API_KEY not found.")
        # If no key, client remains None, crucial check later

    # Load Knowledge Base using the imported function
    print(f"Attempting to load wine knowledge base from: {KNOWLEDGE_DIR}")
    kb, is_single = load_knowledge(KNOWLEDGE_DIR)
    if kb is not None:
        knowledge_base = kb
        is_single_file_load = is_single
        print("Wine knowledge base loaded.")
    else:
        print("Warning: Failed to load wine knowledge base.")
        knowledge_base = None
        is_single_file_load = False

# --- API Endpoints ---
@app.get("/status")
async def get_status():
    """Endpoint to report server status, including dry-run mode."""
    return {"mode": "dry-run" if IS_DRY_RUN else "live"}

@app.post("/query")
async def handle_query(query_request: QueryRequest):
    global client, knowledge_base, is_single_file_load, IS_DRY_RUN  # Access globals

    if not client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")

    query = query_request.query
    print(f"\nReceived query: {query}")

    # Perform RAG using globally loaded knowledge and client
    answer = rag_query(query, knowledge_base, is_single_file_load, client, IS_DRY_RUN)

    # Check if the answer indicates an internal error occurred during RAG
    if isinstance(answer, str) and ("error" in answer.lower() or "not loaded" in answer.lower() or "not initialized" in answer.lower()):
        print(f"[Error] Internal error processing query: {answer}")
        # Check specific known error messages
        if "client is not initialized" in answer:
            raise HTTPException(status_code=500, detail="OpenAI client is not initialized on server.")
        elif "knowledge base not loaded" in answer:
            raise HTTPException(status_code=500, detail="Wine knowledge base is not loaded on server.")
        else:
            raise HTTPException(status_code=500, detail="An internal error occurred while processing the query.")
    else:
        return {"answer": answer}

# --- Run Server ---
if __name__ == '__main__':
    # Setup argument parser for server startup flags
    server_parser = argparse.ArgumentParser(description="Run Wine-AI RAG Server with OpenAI API.")
    server_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the server in dry-run mode (no actual API calls)."
    )
    server_args = server_parser.parse_args()

    # Initialize app with dry-run status
    initialize_app(dry_run_mode=server_args.dry_run)

    print(f"Starting Wine-AI FastAPI server on http://localhost:8080 (Mode: {'dry-run' if IS_DRY_RUN else 'live'})")
    uvicorn.run(app, host="127.0.0.1", port=8080) 