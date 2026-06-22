# Hyundai Knowledge Assistant

A production-ready retrieval-based chatbot that answers Hyundai showroom FAQs using semantic search. There is **no LLM, no generation** — every answer comes directly from the Excel knowledge base.

## How it works

```
User Question → Sentence-Transformer Embedding → ChromaDB Similarity Search → Stored FAQ Answer
```

If no FAQ matches above the confidence threshold, the system returns **"Sorry, no data found."**

---

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Frontend   | React 18, Vite 6, plain CSS             |
| Backend    | FastAPI, Uvicorn                        |
| Vector DB  | ChromaDB (persistent, local)            |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Data       | Pandas + openpyxl (reads `.xlsx`)       |

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

First startup downloads `all-MiniLM-L6-v2` (~90 MB) from HuggingFace and ingests the Excel file into ChromaDB. Subsequent startups are instant.

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
| `EMBEDDING_MODEL`     | `all-MiniLM-L6-v2`         | HuggingFace sentence-transformer model name  |
| `SIMILARITY_THRESHOLD`| `0.55`                     | Minimum cosine similarity to return an answer |
| `CORS_ORIGINS`        | `http://localhost:5173`    | Comma-separated allowed frontend origins     |

### Updating the knowledge base

Replace or edit `data/hyundai_faq.xlsx`. On next backend restart, ChromaDB detects the file hash changed and automatically re-ingests everything.

---

## Features

- ChatGPT-style dark UI with collapsible sidebar
- Persistent chat history (localStorage)
- Welcome screen with clickable suggestion prompts
- Animated typing indicator during search
- Knowledge base stats panel (FAQ count, model, status)
- Semantic search — understands paraphrases without keyword matching
- Zero LLM, zero external API calls, zero data leaving your machine
