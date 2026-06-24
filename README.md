# Hyundai Knowledge Assistant

A full-stack retrieval-based chatbot for Hyundai showroom FAQs, test drive booking, auth with email OTP, and admin monitoring. There is **no LLM generation** — every answer comes from the Excel knowledge base via semantic search.

**Full documentation:** `Hyundai_Knowledge_Assistant_Project_Documentation.docx` (generate with `python generate_documentation.py`)

## How it works

```
User Question → Context resolution → BGE-M3 Embedding → ChromaDB Search → Stored FAQ Answer
```

Each FAQ row = one indexed unit (atomic Q&A chunk). Questions are embedded; answers stored in metadata.

---

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Frontend   | React 18, Vite 6, plain CSS             |
| Backend    | FastAPI, Uvicorn, SQLAlchemy            |
| Database   | SQLite (users, bookings, sessions, logs)|
| Vector DB  | ChromaDB (persistent, cosine HNSW)      |
| Embeddings | `BAAI/bge-m3` via sentence-transformers |
| Data       | Pandas + openpyxl (165 FAQ pairs)       |
| Email      | Gmail SMTP (OTP)                        |

---

## Project Structure

```
Hyundai_chatbot/
├── data/
│   └── hyundai_faq.xlsx          ← FAQ knowledge base (Question | Answer)
│
├── backend/
│   ├── app.py                    ← FastAPI application
│   ├── chroma_db.py              ← ChromaDB vector store wrapper
│   ├── embeddings.py             ← Sentence-Transformer embedding utility
│   ├── data_loader.py            ← Excel ingestion + change detection
│   ├── config.py                 ← All configuration (env-driven)
│   ├── requirements.txt
│   ├── .env.example
│   └── chroma_db/                ← Persisted ChromaDB data (auto-created)
│
└── frontend/
    ├── src/
    │   ├── components/           ← Sidebar, Header, ChatArea, MessageBubble, …
    │   ├── pages/ChatPage.jsx    ← Main page orchestrator
    │   ├── services/api.js       ← Backend fetch helpers
    │   ├── hooks/useChatHistory.js ← LocalStorage chat history
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css             ← Full dark theme
    ├── index.html
    ├── vite.config.js
    └── package.json
```

---

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+

### 1. Backend

```powershell
cd backend
pip install -r requirements.txt
```

First startup downloads `BAAI/bge-m3` (~2GB) from HuggingFace and ingests FAQs into ChromaDB. Subsequent startups are fast if Excel unchanged.

### 2. Frontend

```powershell
cd frontend
npm install
```

---

## Running the Application

Open **two** terminal windows.

### Terminal 1 — Backend

```powershell
cd backend
uvicorn app:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Docs: `http://localhost:8000/docs`

### Terminal 2 — Frontend

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## API Reference

### `POST /chat`

```json
// Request
{ "message": "How much does the Creta cost?" }

// Success response
{ "answer": "Creta starts at ₹11 lakh.", "found": true }

// No-match response
{ "answer": "Sorry, no data found.", "found": false }
```

### `GET /stats`

Returns knowledge base information: FAQ count, ChromaDB document count, embedding model, status.

### `GET /health`

Returns `{ "status": "ok" }`.

---

## Configuration

Copy `backend/.env.example` to `backend/.env` and adjust:

| Variable              | Default                    | Description                                  |
|-----------------------|----------------------------|----------------------------------------------|
| `EXCEL_PATH`          | `../data/hyundai_faq.xlsx` | Path to the FAQ Excel file                   |
| `CHROMA_PERSIST_DIR`  | `./chroma_db`              | Where ChromaDB stores its data               |
| `EMBEDDING_MODEL`     | `BAAI/bge-m3`              | HuggingFace embedding model name             |
| `SIMILARITY_THRESHOLD`| `0.55`                     | Minimum cosine similarity to return an answer |
| `CORS_ORIGINS`        | `http://localhost:5173`    | Comma-separated allowed frontend origins     |

### Updating the knowledge base

Replace or edit `data/hyundai_faq.xlsx`. On next backend restart, ChromaDB detects the file hash changed and automatically re-ingests everything.

---

## Features

- Semantic FAQ search with topic + vehicle re-ranking
- Session context (follow-ups like "its mileage" after asking about Creta)
- Clarification prompts when car model is unknown
- User auth with email OTP, test drive booking, admin dashboard
- Sidebar: last 5 Q&A history; chat logs with IST timestamps for admin
- Code comments in all core files — see documentation Section 15 for reading order
