import os
import json
import string
import random
import time
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, List, Tuple
import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
TOKEN_LENGTH = 6
TOKEN_EXPIRY_HOURS = int(os.getenv('TOKEN_EXPIRY_HOURS', '24'))  # Default to 24 hours if not set
TOKEN_FILE = "server/tokens.json"
EXPIRED_TOKEN_FILE = "server/expired_tokens.json"
TOKEN_CHARS = string.ascii_uppercase + string.digits  # A-Z and 0-9

# Email configuration from environment variables
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_ENABLED = all([EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD])

# Initialize token storage
def init_token_storage() -> None:
    """Initialize token storage file if it doesn't exist"""
    if not os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "w") as f:
            json.dump({"tokens": []}, f)
        logger.info(f"Token storage initialized at {TOKEN_FILE}")
    
    if not os.path.exists(EXPIRED_TOKEN_FILE):
        with open(EXPIRED_TOKEN_FILE, "w") as f:
            json.dump({"expired_tokens": []}, f)
        logger.info(f"Expired token storage initialized at {EXPIRED_TOKEN_FILE}")

# Load tokens from storage
def load_tokens() -> List[Dict]:
    """Load tokens from storage file"""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                return data.get("tokens", [])
        return []
    except Exception as e:
        logger.error(f"Error loading tokens: {e}")
        return []

# Load expired tokens
def load_expired_tokens() -> List[Dict]:
    """Load expired tokens from storage file"""
    try:
        if os.path.exists(EXPIRED_TOKEN_FILE):
            with open(EXPIRED_TOKEN_FILE, "r") as f:
                data = json.load(f)
                return data.get("expired_tokens", [])
        return []
    except Exception as e:
        logger.error(f"Error loading expired tokens: {e}")
        return []

# Save tokens to storage
def save_tokens(tokens: List[Dict]) -> None:
    """Save tokens to storage file"""
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump({"tokens": tokens}, f)
    except Exception as e:
        logger.error(f"Error saving tokens: {e}")

# Save expired tokens to storage
def save_expired_tokens(tokens: List[Dict]) -> None:
    """Save expired tokens to storage file"""
    try:
        with open(EXPIRED_TOKEN_FILE, "w") as f:
            json.dump({"expired_tokens": tokens}, f)
    except Exception as e:
        logger.error(f"Error saving expired tokens: {e}")

# Generate a new token
def generate_token() -> str:
    """Generate a random 6-character alphanumeric token"""
    return ''.join(random.choice(TOKEN_CHARS) for _ in range(TOKEN_LENGTH))

# Create a new token for a user
def create_token(email: str) -> str:
    """Create a new token for the given email"""
    # Load existing tokens
    tokens = load_tokens()
    
    # Remove any existing tokens for this email
    tokens = [t for t in tokens if t.get("email") != email]
    
    # Generate a new token
    token = generate_token()
    expiry = int(time.time() + TOKEN_EXPIRY_HOURS * 3600)
    
    # Add the new token
    tokens.append({
        "email": email,
        "token": token,
        "expiry": expiry,
        "created": int(time.time())
    })
    
    # Save tokens
    save_tokens(tokens)
    
    return token

# Validate a token
def validate_token(token: str) -> bool:
    """Check if a token is valid"""
    if not token:
        return False
        
    # Normalize token (uppercase)
    token = token.upper()
    
    # Load tokens
    tokens = load_tokens()
    
    # Check if token exists and is not expired
    current_time = int(time.time())
    for t in tokens:
        if t.get("token") == token and t.get("expiry", 0) > current_time:
            return True
    
    return False

# Get email for a token
def get_email_for_token(token: str) -> Optional[str]:
    """Get the email associated with a token"""
    if not token:
        return None
        
    # Normalize token (uppercase)
    token = token.upper()
    
    # Check active tokens
    tokens = load_tokens()
    for t in tokens:
        if t.get("token") == token:
            return t.get("email")
    
    # If not found in active tokens, check expired tokens
    expired_tokens = load_expired_tokens()
    for t in expired_tokens:
        if t.get("token") == token:
            return t.get("email")
    
    return None

# Clean up expired tokens
def cleanup_tokens() -> None:
    """Move expired tokens to expired_tokens file instead of deleting them"""
    tokens = load_tokens()
    expired_tokens = load_expired_tokens()
    current_time = int(time.time())
    
    # Find expired tokens
    active_tokens = []
    newly_expired = []
    
    for t in tokens:
        if t.get("expiry", 0) > current_time:
            active_tokens.append(t)
        else:
            # Add expiry timestamp for reference
            t["expired_at"] = current_time
            newly_expired.append(t)
    
    # If we found expired tokens
    if len(newly_expired) > 0:
        logger.info(f"Moving {len(newly_expired)} expired tokens to expired_tokens file")
        
        # Add to expired tokens list
        expired_tokens.extend(newly_expired)
        
        # Save both files
        save_tokens(active_tokens)
        save_expired_tokens(expired_tokens)

# Email a token to a user
def send_token_email(email: str, token: str) -> Tuple[bool, str]:
    """
    Send the token to the user's email
    
    Returns:
        Tuple[bool, str]: (success, mode)
        - success: Whether the operation was successful
        - mode: 'email' if sent by email, 'display' if should be displayed to user
    """
    # Log for debugging regardless of email sending success
    logger.info(f"Sending token '{token}' to {email}")
    
    # If email is not configured, log and return display mode
    if not EMAIL_ENABLED:
        logger.warning("Email sending not configured. Token will be displayed to user.")
        return (True, "display")
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "葡萄酒智能助手 - 您的访问令牌"
        msg['From'] = EMAIL_FROM
        msg['To'] = email
        
        # Create plain text version
        text = f"""
您好，

这是您请求的葡萄酒智能助手访问令牌：

{token}

此令牌有效期为 {TOKEN_EXPIRY_HOURS} 小时。

谢谢！
葡萄酒智能助手团队
        """
        
        # Create HTML version
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ color: #722f37; text-align: center; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
        .content {{ padding: 20px 0; }}
        .token {{ font-size: 24px; font-weight: bold; text-align: center; 
                 padding: 15px; margin: 20px 0; color: #722f37; 
                 border: 1px dashed #ccc; background-color: #f9f9f9; }}
        .footer {{ padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #777; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>葡萄酒智能助手</h1>
        </div>
        <div class="content">
            <p>您好，</p>
            <p>这是您请求的葡萄酒智能助手访问令牌：</p>
            <div class="token">{token}</div>
            <p>此令牌有效期为 {TOKEN_EXPIRY_HOURS} 小时。</p>
            <p>请使用此令牌访问葡萄酒智能助手。</p>
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿回复。</p>
            <p>© 葡萄酒智能助手团队</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Attach parts
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Setup server connection
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        if EMAIL_USE_TLS:
            server.starttls()
        
        # Login if credentials are provided
        if EMAIL_USER and EMAIL_PASSWORD:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
        
        # Send email
        server.sendmail(EMAIL_FROM, email, msg.as_string())
        server.quit()
        
        logger.info(f"Successfully sent token email to {email}")
        return (True, "email")
        
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
        return (False, "display")

# Get all tokens for an email
def get_tokens_for_email(email: str) -> List[Dict]:
    """Get all tokens (active and expired) associated with an email"""
    if not email:
        return []
    
    result = []
    
    # Check active tokens
    active_tokens = load_tokens()
    for t in active_tokens:
        if t.get("email") == email:
            t_copy = t.copy()
            t_copy["status"] = "active"
            result.append(t_copy)
    
    # Check expired tokens
    expired_tokens = load_expired_tokens()
    for t in expired_tokens:
        if t.get("email") == email:
            t_copy = t.copy()
            t_copy["status"] = "expired"
            result.append(t_copy)
    
    # Sort by creation time (newest first)
    result.sort(key=lambda x: x.get("created", 0), reverse=True)
    
    return result

# Get token usage history
def get_token_history(limit: int = 50) -> List[Dict]:
    """Get token usage history (most recent tokens first)"""
    result = []
    
    # Get active tokens
    active_tokens = load_tokens()
    for t in active_tokens:
        t_copy = t.copy()
        t_copy["status"] = "active"
        result.append(t_copy)
    
    # Get expired tokens
    expired_tokens = load_expired_tokens()
    for t in expired_tokens:
        t_copy = t.copy()
        t_copy["status"] = "expired"
        result.append(t_copy)
    
    # Sort by creation time (newest first)
    result.sort(key=lambda x: x.get("created", 0), reverse=True)
    
    # Limit results
    return result[:limit]

# Clear expired tokens older than a certain time
def clear_old_expired_tokens(days: int = 90) -> int:
    """
    Clear expired tokens older than the specified number of days
    Returns the number of tokens cleared
    """
    expired_tokens = load_expired_tokens()
    current_time = int(time.time())
    cutoff_time = current_time - (days * 24 * 3600)
    
    # Filter out tokens older than cutoff
    new_expired_tokens = [t for t in expired_tokens if t.get("expired_at", 0) > cutoff_time]
    
    # Calculate how many were removed
    tokens_cleared = len(expired_tokens) - len(new_expired_tokens)
    
    if tokens_cleared > 0:
        logger.info(f"Cleared {tokens_cleared} expired tokens older than {days} days")
        save_expired_tokens(new_expired_tokens)
    
    return tokens_cleared 