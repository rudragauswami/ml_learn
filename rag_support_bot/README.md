# Context-Aware Customer Support Bot (RAG)

A highly accurate Retrieval-Augmented Generation (RAG) Customer Support Bot built in Python. This bot prevents "hallucinations" by strictly answering questions using a private knowledge base (provided in `data/knowledge_base.txt`).

**Tech Stack:** 
- **Language**: Python
- **Orchestration**: LangChain
- **Embeddings**: HuggingFace (`all-MiniLM-L6-v2`) — *runs locally, 100% free.*
- **Vector Database**: ChromaDB — *runs locally in a `.chroma_db` folder.*
- **LLM**: Groq (Llama-3) — *insanely fast, free tier available.*

## 1. Setup

### 1.1 Install Dependencies
Make sure you have a Python virtual environment set up (recommended, e.g. `python -m venv venv`), then install the requirements:
```bash
pip install -r requirements.txt
```

### 1.2 Get a Groq API Key
1. Go to [console.groq.com](https://console.groq.com/) and create a free account.
2. Generate an API key.
3. Rename `.env.example` to `.env` in this directory.
4. Paste your API key into `.env`: `GROQ_API_KEY="gsk_..."`

## 2. Running the RAG Bot

This is a two-step process: **Ingestion** (creating the database) and **Retrieval** (chatting).

### Step 1: Ingest standard data
First, you need to turn the human-readable text in `data/` into mathematical vectors and store them.
```bash
python ingest.py
```
*You only need to run this once, or whenever you modify the text files in `data/`.*

### Step 2: Chat with the Bot
Spin up the customer support bot and test its knowledge:
```bash
python bot.py
```
Try asking out-of-bounds questions (like "What is the capital of France?") to see how the RAG architecture actively prevents hallucination.
