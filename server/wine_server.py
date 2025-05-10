import os
from dotenv import load_dotenv
import openai
import argparse
import uvicorn
from fastapi import FastAPI, HTTPException, Request, APIRouter, Depends, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, EmailStr
from rag_utils import load_knowledge, rag_query, KNOWLEDGE_DIR
import logger
import acl
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_307_TEMPORARY_REDIRECT, HTTP_401_UNAUTHORIZED
from datetime import datetime
from acl import TOKEN_EXPIRY_HOURS

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
app = FastAPI(title="葡萄酒智能助手 API", description="使用LLM的葡萄酒知识检索API")

# Create API router with prefix
api_router = APIRouter(prefix="/api")

# Create admin router with prefix
admin_router = APIRouter(prefix="/admin")

# Define request models
class QueryRequest(BaseModel):
    query: str

class TokenRequest(BaseModel):
    email: EmailStr

class EmailRequest(BaseModel):
    email: EmailStr

# Token header
API_KEY_HEADER = APIKeyHeader(name="X-API-Token", auto_error=False)

# --- Token Validation Middleware ---
class TokenValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip token validation for token request endpoints and static files
        if (request.url.path == "/request-token" or 
            request.url.path == "/api/request-token" or
            request.url.path == "/submit-token-request"):
            return await call_next(request)
            
        # Get token from header or cookie
        token = request.headers.get("X-API-Token")
        if not token:
            # Try getting from cookie
            token = request.cookies.get("wine_ai_token")
            
        # Validate token
        if token and acl.validate_token(token):
            # Token is valid, proceed with request
            return await call_next(request)
        else:
            # Token is invalid or missing, redirect to token request page
            if "application/json" in request.headers.get("accept", ""):
                # API request, return 401
                return Response(
                    status_code=HTTP_401_UNAUTHORIZED,
                    content="Unauthorized: Valid token required",
                    media_type="text/plain"
                )
            else:
                # Browser request, redirect to token request page
                return RedirectResponse(
                    url="/request-token",
                    status_code=HTTP_307_TEMPORARY_REDIRECT
                )

# Add middleware to app
app.add_middleware(TokenValidationMiddleware)

def initialize_app(dry_run_mode=False):
    global client, knowledge_base, is_single_file_load, IS_DRY_RUN
    IS_DRY_RUN = dry_run_mode
    logger.info(f"Initializing Wine-AI RAG server... (Dry Run: {IS_DRY_RUN})")
    
    # Initialize token storage
    acl.init_token_storage()
    logger.info("ACL token system initialized")
    
    # Clean up expired tokens
    acl.cleanup_tokens()

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

@api_router.post("/request-token")
async def request_token(token_request: TokenRequest):
    """Request a new access token"""
    email = token_request.email
    logger.info(f"Token request received for email: {email}")
    
    # Generate token
    token = acl.create_token(email)
    
    # Send token via email (or prepare to display to user)
    success, mode = acl.send_token_email(email, token)
    
    if mode == "display":
        # Return token directly to client if email is not sent
        return {
            "message": "令牌已生成。请保存此令牌，它不会通过电子邮件发送。",
            "token": token,
            "display_token": True
        }
    else:
        # Normal message when email is sent
        return {"message": "Token generated and sent to your email"}

# --- Add Token Request UI endpoints ---
@app.get("/request-token", response_class=HTMLResponse)
async def token_request_page():
    """Token request HTML form"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>请求访问令牌 - 葡萄酒智能助手</title>
        <style>
            body {
                font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: #f9f7f3;
                color: #333;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 500px;
                width: 100%;
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            h1 {
                color: #722f37;
                margin-bottom: 20px;
                text-align: center;
            }
            p {
                margin-bottom: 20px;
                line-height: 1.6;
            }
            form {
                display: flex;
                flex-direction: column;
            }
            label {
                margin-bottom: 8px;
                font-weight: bold;
            }
            input[type="email"] {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-bottom: 20px;
                font-size: 16px;
            }
            button {
                background-color: #722f37;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
            }
            button:hover {
                background-color: #5a252c;
            }
            .error {
                color: #a4243b;
                margin-top: 20px;
                text-align: center;
            }
            .success {
                color: #2e7d32;
                margin-top: 20px;
                text-align: center;
                padding: 10px;
                background-color: #e8f5e9;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>获取访问令牌</h1>
            <p>请输入您的电子邮件地址以获取访问葡萄酒智能助手的令牌。令牌将发送到您的邮箱，有效期为24小时。</p>
            
            <form action="/submit-token-request" method="post">
                <label for="email">电子邮件地址:</label>
                <input type="email" id="email" name="email" required placeholder="请输入您的电子邮件地址">
                <button type="submit">获取令牌</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.post("/submit-token-request", response_class=HTMLResponse)
async def submit_token_request(email: str = Form(...)):
    """Process token request form submission"""
    # Generate token
    token = acl.create_token(email)
    
    # Send token via email (or prepare to display to user)
    success, mode = acl.send_token_email(email, token)
    
    # Display message based on email sending mode
    email_sent_msg = "并已发送到您的邮箱。" if mode == "email" else "。请保存好此令牌，它不会通过电子邮件发送。"
    
    # Return success page with token
    success_html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>令牌已发送 - 葡萄酒智能助手</title>
        <style>
            body {{
                font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: #f9f7f3;
                color: #333;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 500px;
                width: 100%;
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #722f37;
                margin-bottom: 20px;
                text-align: center;
            }}
            p {{
                margin-bottom: 20px;
                line-height: 1.6;
            }}
            .success {{
                color: #2e7d32;
                margin: 20px 0;
                text-align: center;
                padding: 15px;
                background-color: #e8f5e9;
                border-radius: 4px;
            }}
            .token {{
                font-size: 24px;
                font-weight: bold;
                text-align: center;
                margin: 20px 0;
                letter-spacing: 2px;
                color: #722f37;
            }}
            .button {{
                background-color: #722f37;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                display: block;
                width: 100%;
                text-decoration: none;
            }}
            .button:hover {{
                background-color: #5a252c;
            }}
            .token-warning {{
                font-weight: bold;
                color: #e53935;
                margin-top: 10px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>令牌已生成</h1>
            <div class="success">
                <p>您的访问令牌已成功生成{email_sent_msg}</p>
            </div>
            
            <p>您的令牌是:</p>
            <div class="token">{token}</div>
            <p>此令牌有效期为{TOKEN_EXPIRY_HOURS}小时。请使用此令牌访问葡萄酒智能助手。</p>
            
            {f'<p class="token-warning">请立即复制并保存此令牌，关闭此页面后将无法再次查看！</p>' if mode == "display" else ''}
            
            <a href="/" class="button">返回首页</a>
        </div>
    </body>
    </html>
    """
    
    # Set token cookie for browser
    response = HTMLResponse(content=success_html)
    response.set_cookie(
        key="wine_ai_token", 
        value=token,
        max_age=TOKEN_EXPIRY_HOURS * 3600,
        httponly=True,
        samesite="lax"
    )
    
    return response

# --- Include routers in the main application ---
app.include_router(api_router)
app.include_router(admin_router)

# --- Add backward compatibility endpoints ---
@app.get("/status")
async def legacy_status():
    """Legacy endpoint for backward compatibility"""
    return await get_status()

@app.post("/query")
async def legacy_query(query_request: QueryRequest):
    """Legacy endpoint for backward compatibility"""
    return await handle_query(query_request)

# --- Add Admin API Endpoints ---
@admin_router.get("/tokens")
async def get_token_history(limit: int = 50):
    """Get token usage history"""
    tokens = acl.get_token_history(limit)
    
    # Format timestamps for readability
    for token in tokens:
        created = token.get("created", 0)
        expiry = token.get("expiry", 0)
        expired_at = token.get("expired_at", 0)
        
        token["created_time"] = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S") if created else "Unknown"
        token["expiry_time"] = datetime.fromtimestamp(expiry).strftime("%Y-%m-%d %H:%M:%S") if expiry else "Unknown"
        if expired_at:
            token["expired_time"] = datetime.fromtimestamp(expired_at).strftime("%Y-%m-%d %H:%M:%S")
    
    return {"tokens": tokens}

@admin_router.post("/tokens/user")
async def get_user_tokens(email_request: EmailRequest):
    """Get all tokens for a specific user"""
    tokens = acl.get_tokens_for_email(email_request.email)
    
    # Format timestamps for readability
    for token in tokens:
        created = token.get("created", 0)
        expiry = token.get("expiry", 0)
        expired_at = token.get("expired_at", 0)
        
        token["created_time"] = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S") if created else "Unknown"
        token["expiry_time"] = datetime.fromtimestamp(expiry).strftime("%Y-%m-%d %H:%M:%S") if expiry else "Unknown"
        if expired_at:
            token["expired_time"] = datetime.fromtimestamp(expired_at).strftime("%Y-%m-%d %H:%M:%S")
    
    return {"email": email_request.email, "tokens": tokens}

@admin_router.post("/tokens/cleanup")
async def cleanup_old_tokens(days: int = 90):
    """Clean up expired tokens older than specified days"""
    cleared = acl.clear_old_expired_tokens(days)
    return {"cleared": cleared, "message": f"Cleared {cleared} expired tokens older than {days} days"}

@admin_router.get("/email-for-token/{token}")
async def get_email_for_token(token: str):
    """Get the email associated with a token"""
    email = acl.get_email_for_token(token)
    if email:
        return {"token": token, "email": email}
    else:
        raise HTTPException(status_code=404, detail="Token not found")

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