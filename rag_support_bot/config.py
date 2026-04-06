import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
    CHROMA_DB_DIR = ".chroma_db"
    LLM_MODEL_NAME = "llama3-8b-8192"
    LLM_TEMPERATURE = 0
    DATA_DIR = "data"
