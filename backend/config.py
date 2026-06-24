"""
Application configuration — loads environment variables from backend/.env.

All paths are absolute (resolved from PROJECT_ROOT) so the app works
regardless of which directory you start uvicorn from.

Key settings:
  - EXCEL_PATH: source FAQ data
  - CHROMA_PERSIST_DIR: vector database storage on disk
  - SIMILARITY_THRESHOLD: minimum cosine similarity to return an answer (0.55)
  - JWT_* / SMTP_*: authentication and email OTP
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# BASE_DIR = backend/ folder; PROJECT_ROOT = Hyundai_chatbot/ folder
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")  # load_dotenv reads KEY=value pairs into os.environ

# --- File paths ---
DATA_DIR = PROJECT_ROOT / "data"
EXCEL_PATH = DATA_DIR / "hyundai_faq.xlsx"
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_db"
INGESTION_META_PATH = CHROMA_PERSIST_DIR / "ingestion_meta.json"
DATABASE_URL = f"sqlite:///{BASE_DIR / 'app.db'}"  # SQLite file-based database

# Fail fast at import time if FAQ file is missing
if not EXCEL_PATH.exists():
    raise FileNotFoundError(f"Excel file not found: {EXCEL_PATH}\nPlease ensure hyundai_faq.xlsx is in the data/ folder")

# --- ChromaDB ---
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "hyundai_faq")

# --- Embeddings (Hugging Face model name) ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

# Chroma cosine distance = 1 - cosine_similarity; threshold 0.55 ≈ reasonably confident match
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.55"))

# --- JWT authentication ---
JWT_SECRET = os.getenv("JWT_SECRET", "hyundai-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours

# --- Gmail SMTP for OTP emails ---
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "")  # Gmail app passwords often have spaces
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL") or SMTP_USER
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

# Comma-separated list of allowed frontend origins for CORS
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174,"
    "http://localhost:5175,http://127.0.0.1:5175",
).split(",")
