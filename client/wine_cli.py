import requests
import sys
import json
import os.path
import getpass

QUERY_URL = "http://localhost:8080/api/query"
STATUS_URL = "http://localhost:8080/api/status"
TOKEN_REQUEST_URL = "http://localhost:8080/api/request-token"
TOKEN_FILE = os.path.expanduser("~/.wine_ai_token")

def get_server_status():
    """Checks the server status endpoint."""
    try:
        response = requests.get(STATUS_URL, timeout=5)  # Short timeout for status check
        response.raise_for_status()
        data = response.json()
        return data.get("mode", "unknown")  # Return 'live', 'dry-run', or 'unknown'
    except requests.exceptions.RequestException as e:
        print(f"[警告] 无法获取服务器状态 {STATUS_URL}: {e}")
        return "unknown"
    except json.JSONDecodeError:
        print(f"[警告] 无法解析服务器状态响应 {STATUS_URL}.")
        return "unknown"

def load_token():
    """Load token from file if it exists"""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                return f.read().strip()
        except Exception as e:
            print(f"[警告] 读取令牌文件时出错: {e}")
    return None

def save_token(token):
    """Save token to file"""
    try:
        with open(TOKEN_FILE, "w") as f:
            f.write(token)
        # Set permissions to user-only read/write
        os.chmod(TOKEN_FILE, 0o600)
    except Exception as e:
        print(f"[警告] 保存令牌文件时出错: {e}")

def request_new_token():
    """Request a new token from the server"""
    print("您需要一个访问令牌才能继续。")
    
    while True:
        # Get email from user
        email = input("请输入您的电子邮件地址: ").strip()
        if not email or "@" not in email:
            print("请输入一个有效的电子邮件地址。")
            continue
            
        # Request token from server
        try:
            response = requests.post(TOKEN_REQUEST_URL, json={"email": email}, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Check if token is directly returned (no email configuration)
            if "display_token" in data and data["display_token"] and "token" in data:
                token = data["token"]
                print(f"{data.get('message', '令牌已生成')}")
                print(f"您的令牌是: {token}")
                print("请保存此令牌，它在24小时内有效。")
                save_token(token)
                return token
            else:
                # Normal flow - token sent by email
                print(f"令牌请求已提交。请检查您的电子邮件 ({email}) 获取令牌。")
                
                # Get token from user
                token = input("请输入您收到的令牌: ").strip().upper()
                if token:
                    save_token(token)
                    return token
                
        except requests.exceptions.RequestException as e:
            print(f"[错误] 请求令牌时出错: {e}")
            if input("是否重试? (y/n): ").lower() != 'y':
                return None

def run_chat_client():
    print("--- 葡萄酒知识库聊天客户端 ---")

    # Check server status at startup
    server_mode = get_server_status()
    if server_mode == "dry-run":
        print(f"*** 已连接到服务器: {QUERY_URL} (测试模式) ***")
    elif server_mode == "live":
        print(f"已连接到服务器: {QUERY_URL} (在线模式)")
    else:
        print(f"已连接到服务器: {QUERY_URL} (状态未知)")

    # Get token
    token = load_token()
    if not token:
        token = request_new_token()
        if not token:
            print("错误: 无法获取有效的访问令牌。")
            return

    print("请输入您的葡萄酒相关问题，或输入 'quit' 或 'exit' 退出。")
    print("输入 'token' 可更新您的访问令牌。")

    while True:
        try:
            query = input("\n您: ")
            query = query.strip()

            if not query:
                continue

            if query.lower() in ["quit", "exit"]:
                print("再见！")
                break
                
            if query.lower() == "token":
                token = request_new_token()
                if not token:
                    print("警告: 继续使用现有令牌。")
                else:
                    print("令牌已更新。")
                continue

            # Prepare JSON payload
            payload = {"query": query}
            headers = {"X-API-Token": token}

            # Send request to server
            try:
                response = requests.post(QUERY_URL, json=payload, headers=headers, timeout=60)
                
                if response.status_code == 401:
                    print("访问令牌已过期或无效。请获取新令牌。")
                    token = request_new_token()
                    if not token:
                        print("错误: 无法获取有效的访问令牌。")
                        break
                    # Retry with new token
                    response = requests.post(QUERY_URL, json=payload, headers={"X-API-Token": token}, timeout=60)
                
                response.raise_for_status()

                # Process successful response
                try:
                    data = response.json()
                    if "answer" in data:
                        print(f"葡萄酒助手: {data['answer']}")
                    elif "detail" in data:  # FastAPI error format
                        print(f"服务器错误: {data['detail']}")
                    else:
                        print("葡萄酒助手: (收到未知响应)")
                except json.JSONDecodeError:
                    print(f"错误: 无法解析服务器响应: {response.text}")

            except requests.exceptions.ConnectionError:
                print(f"错误: 无法连接到服务器 {QUERY_URL}。 请确保服务器正在运行。")
            except requests.exceptions.Timeout:
                print(f"错误: 请求超时 ({QUERY_URL})。")
            except requests.exceptions.RequestException as e:
                # Catch other request exceptions (like HTTPError raised by raise_for_status)
                print(f"请求错误: {e}")
                # Try to print server error message if available
                try:
                    error_data = response.json()
                    if "detail" in error_data:  # FastAPI error format
                        print(f"服务器详细错误: {error_data['detail']}")
                except (json.JSONDecodeError, NameError, AttributeError):
                    pass  # Ignore if response wasn't JSON or response object doesn't exist

        except EOFError:  # Handle Ctrl+D
            print("\n再见！")
            break
        except KeyboardInterrupt:  # Handle Ctrl+C
            print("\n再见！")
            break

if __name__ == "__main__":
    run_chat_client() 