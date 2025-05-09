import requests
import sys
import json

QUERY_URL = "http://localhost:8080/api/query"
STATUS_URL = "http://localhost:8080/api/status"

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

    print("请输入您的葡萄酒相关问题，或输入 'quit' 或 'exit' 退出。")

    while True:
        try:
            query = input("\n您: ")
            query = query.strip()

            if not query:
                continue

            if query.lower() in ["quit", "exit"]:
                print("再见！")
                break

            # Prepare JSON payload
            payload = {"query": query}

            # Send request to server
            try:
                response = requests.post(QUERY_URL, json=payload, timeout=60)
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