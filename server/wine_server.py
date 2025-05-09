import os
from dotenv import load_dotenv
import openai
import argparse
import uvicorn
from fastapi import FastAPI, HTTPException, Request, APIRouter
from pydantic import BaseModel
from rag_utils import load_knowledge, rag_query, KNOWLEDGE_DIR
import logger

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
app = FastAPI(title="葡萄酒智能助手 API", description="使用OpenAI的葡萄酒知识检索API")

# Create API router with prefix
api_router = APIRouter(prefix="/api")

# Define request model
class QueryRequest(BaseModel):
    query: str

def initialize_app(dry_run_mode=False):
    global client, knowledge_base, is_single_file_load, IS_DRY_RUN
    IS_DRY_RUN = dry_run_mode
    logger.info(f"Initializing Wine-AI RAG server... (Dry Run: {IS_DRY_RUN})")

    # Initialize OpenAI Client
    if llm_api_key:
        logger.info("Attempting to initialize OpenAI client...")
        try:
            client = openai.OpenAI(
                api_key=llm_api_key,
                base_url=api_base_url
            )
            logger.info("OpenAI client initialized successfully.")
        except Exception as e:
            logger.critical(f"Fatal: Error initializing OpenAI client: {e}")
            client = None
    else:
        logger.critical("Fatal: LLM_API_KEY not found.")
        # If no key, client remains None, crucial check later

    # Load Knowledge Base using the imported function
    logger.info(f"Attempting to load wine knowledge base from: {KNOWLEDGE_DIR}")
    kb, is_single = load_knowledge(KNOWLEDGE_DIR)
    if kb is not None:
        knowledge_base = kb
        is_single_file_load = is_single
        logger.info("Wine knowledge base loaded.")
    else:
        logger.warning("Warning: Failed to load wine knowledge base.")
        knowledge_base = None
        is_single_file_load = False

# --- API Endpoints ---
@api_router.get("/status")
async def get_status():
    """Endpoint to report server status, including dry-run mode."""
    return {"mode": "dry-run" if IS_DRY_RUN else "live"}

@api_router.post("/query")
async def handle_query(query_request: QueryRequest):
    global client, knowledge_base, is_single_file_load, IS_DRY_RUN  # Access globals

    if not client:
        logger.error("OpenAI client not initialized, cannot handle query")
        raise HTTPException(status_code=500, detail="OpenAI客户端未初始化")

    query = query_request.query
    logger.info(f"Received query: {query}")

    # Perform RAG using globally loaded knowledge and client
    answer = rag_query(query, knowledge_base, is_single_file_load, client, IS_DRY_RUN)

    # Check if the answer indicates an internal error occurred during RAG
    if isinstance(answer, str) and ("error" in answer.lower() or "not loaded" in answer.lower() or "not initialized" in answer.lower()):
        logger.error(f"Internal error processing query: {answer}")
        # Check specific known error messages
        if "client is not initialized" in answer:
            raise HTTPException(status_code=500, detail="服务器上的OpenAI客户端未初始化。")
        elif "knowledge base not loaded" in answer:
            raise HTTPException(status_code=500, detail="服务器上的葡萄酒知识库未加载。")
        else:
            raise HTTPException(status_code=500, detail="处理查询时出现内部错误。")
    else:
        return {"answer": answer}

# Include the router in the main application
app.include_router(api_router)

# --- Add backward compatibility endpoints ---
@app.get("/status")
async def legacy_status():
    """Legacy endpoint for backward compatibility"""
    return await get_status()

@app.post("/query")
async def legacy_query(query_request: QueryRequest):
    """Legacy endpoint for backward compatibility"""
    return await handle_query(query_request)

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

    logger.info(f"Starting Wine-AI FastAPI server on http://localhost:8080 (Mode: {'dry-run' if IS_DRY_RUN else 'live'})")
    uvicorn.run(app, host="127.0.0.1", port=8080) 