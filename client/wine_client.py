import requests
import sys
import json

QUERY_URL = "http://localhost:8080/query"
STATUS_URL = "http://localhost:8080/status"

def get_server_status():
    """Checks the server status endpoint."""
    try:
        response = requests.get(STATUS_URL, timeout=5)  # Short timeout for status check
        response.raise_for_status()
        data = response.json()
        return data.get("mode", "unknown")  # Return 'live', 'dry-run', or 'unknown'
    except requests.exceptions.RequestException as e:
        print(f"[Warning] Could not get server status from {STATUS_URL}: {e}")
        return "unknown"
    except json.JSONDecodeError:
        print(f"[Warning] Could not parse server status response from {STATUS_URL}.")
        return "unknown"

def run_chat_client():
    print("--- Wine-AI Knowledge Base Chat Client ---")

    # Check server status at startup
    server_mode = get_server_status()
    if server_mode == "dry-run":
        print(f"*** Connected to server: {QUERY_URL} (dry-run mode) ***")
    elif server_mode == "live":
        print(f"Connected to server: {QUERY_URL} (live mode)")
    else:
        print(f"Connected to server: {QUERY_URL} (status unknown)")

    print("Enter your wine-related questions, or type 'quit' or 'exit' to quit.")

    while True:
        try:
            query = input("\nYou: ")
            query = query.strip()

            if not query:
                continue

            if query.lower() in ["quit", "exit"]:
                print("Goodbye!")
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
                        print(f"Wine Assistant: {data['answer']}")
                    elif "detail" in data:  # FastAPI error format
                        print(f"Server error: {data['detail']}")
                    else:
                        print("Wine Assistant: (Received unknown response)")
                except json.JSONDecodeError:
                    print(f"Error: Unable to parse server response: {response.text}")

            except requests.exceptions.ConnectionError:
                print(f"Error: Could not connect to server {QUERY_URL}. Please ensure the server is running.")
            except requests.exceptions.Timeout:
                print(f"Error: Request timed out ({QUERY_URL}).")
            except requests.exceptions.RequestException as e:
                # Catch other request exceptions (like HTTPError raised by raise_for_status)
                print(f"Request error: {e}")
                # Try to print server error message if available
                try:
                    error_data = response.json()
                    if "detail" in error_data:  # FastAPI error format
                        print(f"Server detailed error: {error_data['detail']}")
                except (json.JSONDecodeError, NameError, AttributeError):
                    pass  # Ignore if response wasn't JSON or response object doesn't exist

        except EOFError:  # Handle Ctrl+D
            print("\nGoodbye!")
            break
        except KeyboardInterrupt:  # Handle Ctrl+C
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    run_chat_client() 