# Wine-AI

Wine-AI is a Retrieval-Augmented Generation (RAG) system designed to answer wine-related questions. It consists of a server that processes queries using a knowledge base of wine information and an OpenAI language model, along with a client application for interacting with the server.

## Features

- Server-client architecture for wine knowledge retrieval
- OpenAI integration for intelligent responses
- FastAPI-powered REST API with automatic documentation
- Context-based question answering using wine knowledge documents
- Support for markdown (.md) knowledge files

## Prerequisites

- Python 3.7 or higher
- OpenAI API key

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/wine-ai.git
   cd wine-ai
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Download NLTK resources (first time only):
   ```python
   python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
   ```

4. Create a `.env` file in the root directory with your OpenAI API key:
   ```
   LLM_API_KEY=your_llm_api_key_here
   ```

## Usage

### Adding Knowledge Files

Place your wine knowledge files in the `data` directory. The system will automatically load all `.md` files in this directory.

### Starting the Server

Run the server:
```
python server/wine_server.py
```

For dry-run mode (no actual API calls):
```
python server/wine_server.py --dry-run
```

The server will start on http://localhost:8080. You can access the API documentation at http://localhost:8080/docs.

### Using the Client

In a separate terminal, run the client:
```
python client/wine_client.py
```

You can then start asking wine-related questions through the client interface.

## System Architecture

- `server/wine_server.py`: The main FastAPI server implementation that handles API requests
- `server/rag_utils.py`: Utility functions for knowledge loading and retrieval
- `client/wine_client.py`: Command-line client for interacting with the server
- `data/`: Directory containing wine knowledge files in markdown format

## Example Queries

- "What's the difference between Cabernet Sauvignon and Merlot?"
- "What wine should I pair with grilled steak?"
- "What's the ideal serving temperature for Champagne?"
- "Tell me about wine regions in France."

## License

This project is open source and available under the [GPL v3 License](LICENSE). 