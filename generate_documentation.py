"""Generate comprehensive Word documentation for Hyundai Knowledge Assistant."""

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUTPUT = "Hyundai_Knowledge_Assistant_Project_Documentation.docx"


def set_cell_shading(cell, color_hex: str) -> None:
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), color_hex)
    cell._tc.get_or_add_tcPr().append(shading)


def add_title_page(doc: Document) -> None:
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("HYUNDAI KNOWLEDGE ASSISTANT\n")
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = RGBColor(0, 44, 95)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run("Complete Project Documentation\n")
    r.font.size = Pt(16)
    r.bold = True

    sub2 = doc.add_paragraph()
    sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = sub2.add_run(
        "Semantic FAQ Chatbot with Authentication, OTP Email, Test Drive Booking & Admin Panel\n\n"
    )
    r2.font.size = Pt(12)

    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    info.add_run("Prepared for: Project Presentation & Viva\n").font.size = Pt(11)
    info.add_run("Version: 2.1.0\n").font.size = Pt(11)
    info.add_run("Stack: React + FastAPI + ChromaDB + SQLite + BGE-M3 Embeddings").font.size = Pt(11)
    doc.add_page_break()


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def add_para(doc: Document, text: str, bold: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold


def add_bullet(doc: Document, text: str) -> None:
    doc.add_paragraph(text, style="List Bullet")


def add_numbered(doc: Document, text: str) -> None:
    doc.add_paragraph(text, style="List Number")


def add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        set_cell_shading(hdr[i], "002C5F")
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
    for row_data in rows:
        row = table.add_row().cells
        for i, val in enumerate(row_data):
            row[i].text = val
    doc.add_paragraph()


def build_document() -> Document:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    add_title_page(doc)

    # TABLE OF CONTENTS (manual)
    add_heading(doc, "Table of Contents", 1)
    toc = [
        "1. Project Overview",
        "2. Problem Statement & Solution",
        "3. System Architecture",
        "4. Technology Stack & Libraries (Detailed)",
        "5. How Semantic Search Works",
        "6. Database Design (SQLite)",
        "7. API Endpoints (Complete List)",
        "8. Authentication & Security",
        "9. Email OTP System (SMTP)",
        "10. Test Drive Booking System",
        "11. Admin Dashboard",
        "12. Frontend Structure",
        "13. Every File Explained",
        "14. Environment Variables",
        "15. How to Run the Project",
        "16. Data Flow Diagrams (Text)",
        "17. Common Viva Questions & Answers",
        "18. Limitations & Future Scope",
        "19. Security Notes Before GitHub",
    ]
    for item in toc:
        add_bullet(doc, item)
    doc.add_page_break()

    # 1. PROJECT OVERVIEW
    add_heading(doc, "1. Project Overview", 1)
    add_para(
        doc,
        "Hyundai Knowledge Assistant is a full-stack web application that helps users get answers "
        "about Hyundai vehicles, book test drives, and manage their account. It is a RETRIEVAL-BASED "
        "chatbot — meaning it does NOT use ChatGPT or any LLM to generate answers. Every answer comes "
        "directly from a pre-defined Excel FAQ knowledge base using semantic (meaning-based) search.",
    )
    add_para(doc, "Key Features:", bold=True)
    features = [
        "Semantic FAQ search powered by ChromaDB vector database and BGE-M3 embeddings",
        "User registration and login with Two-Factor Authentication (OTP via email)",
        "Forgot password and reset password with email OTP",
        "Test drive booking with 1-hour time slots (10 AM to 8 PM)",
        "Slot conflict detection — prevents double booking",
        "Available slot display inside chat (e.g., 'What are available timings for today?')",
        "Dynamic follow-up suggestion chips after each answer",
        "Per-user chat session history (separate for each logged-in user)",
        "Admin dashboard for booking management and chat monitoring",
        "Dark-themed ChatGPT-style user interface",
    ]
    for f in features:
        add_bullet(doc, f)

    # 2. PROBLEM & SOLUTION
    add_heading(doc, "2. Problem Statement & Solution", 1)
    add_para(doc, "Problem:", bold=True)
    add_para(
        doc,
        "Hyundai showroom customers frequently ask repetitive questions about car prices, mileage, "
        "features, warranty, and test drives. Staff cannot answer 24/7. Keyword-based search fails "
        "when users phrase questions differently (e.g., 'Creta cost' vs 'price of Hyundai Creta').",
    )
    add_para(doc, "Solution:", bold=True)
    add_para(
        doc,
        "We built a semantic search chatbot that understands the MEANING of questions, not just exact "
        "keywords. Questions are converted to numerical vectors (embeddings) and compared against "
        "stored FAQ vectors. The closest match above a confidence threshold returns the stored answer. "
        "If no match is found, the system honestly says 'Sorry, no data found.' — no fake AI generation.",
    )

    # 3. ARCHITECTURE
    add_heading(doc, "3. System Architecture", 1)
    add_para(doc, "The project follows a classic 3-tier architecture:", bold=True)
    add_numbered(doc, "Presentation Layer — React frontend (port 5173)")
    add_numbered(doc, "Application Layer — FastAPI backend (port 8000)")
    add_numbered(doc, "Data Layer — SQLite (users/bookings), ChromaDB (FAQ vectors), Excel (source data)")
    add_para(doc, "")
    add_para(doc, "Communication Flow:", bold=True)
    add_para(
        doc,
        "Browser → Vite Dev Server (proxy /api) → FastAPI → ChromaDB/SQLite/Gmail SMTP → Response back to UI",
    )
    add_para(doc, "Frontend proxy (vite.config.js) forwards all /api/* requests to http://127.0.0.1:8000 to avoid CORS issues during development.", bold=False)

    # 4. TECH STACK
    add_heading(doc, "4. Technology Stack & Libraries (Detailed)", 1)

    add_heading(doc, "4.1 Backend Python Libraries", 2)
    backend_libs = [
        ("FastAPI", "Modern Python web framework for building REST APIs. Used to create all HTTP endpoints (/chat, /auth, /bookings, /admin). Provides automatic API documentation, request validation, and dependency injection."),
        ("Uvicorn", "ASGI server that runs the FastAPI application. Command: uvicorn app:app --port 8000. Handles HTTP requests asynchronously."),
        ("ChromaDB", "Open-source vector database. Stores FAQ question embeddings as vectors for fast similarity search. Persists data locally in backend/chroma_db/ folder. Uses cosine distance for comparing vectors."),
        ("sentence-transformers", "Python library for generating text embeddings using pre-trained neural network models. We use BAAI/bge-m3 model which converts text into 1024-dimensional vectors capturing semantic meaning."),
        ("BAAI/bge-m3", "Embedding model (not a separate pip package — downloaded via sentence-transformers). State-of-the-art multilingual embedding model. Better than older models like all-MiniLM-L6-v2 for semantic search accuracy."),
        ("Pandas", "Data analysis library. Used in data_loader.py to read the Excel FAQ file (hyundai_faq.xlsx) and extract Question/Answer columns."),
        ("openpyxl", "Excel file reader engine used by Pandas to parse .xlsx files."),
        ("python-dotenv", "Loads environment variables from backend/.env file into the application. Keeps secrets (SMTP password, JWT secret) out of source code."),
        ("Pydantic", "Data validation library. Defines request/response schemas (e.g., LoginRequest, ChatResponse). FastAPI uses Pydantic to validate incoming JSON automatically."),
        ("SQLAlchemy", "Python ORM (Object-Relational Mapping) for database operations. Maps Python classes (User, Booking) to SQLite tables. Handles queries, inserts, updates without writing raw SQL."),
        ("bcrypt", "Password hashing library. Converts plain-text passwords into secure one-way hashes before storing in database. Never stores actual passwords."),
        ("PyJWT", "JSON Web Token library. Creates and verifies JWT tokens for user authentication. Token contains user ID, email, role, and expiry time."),
        ("python-multipart", "Required by FastAPI for parsing form data and file uploads."),
        ("smtplib (built-in)", "Python standard library for sending emails via SMTP protocol. Used to send OTP verification emails through Gmail."),
        ("email.mime (built-in)", "Python standard library for constructing HTML and plain-text email messages."),
    ]
    add_table(doc, ["Library", "Purpose & Usage in This Project"], backend_libs)

    add_heading(doc, "4.2 Frontend JavaScript Libraries", 2)
    frontend_libs = [
        ("React 18", "JavaScript UI library for building interactive user interfaces using components. Every screen element (chat, modals, sidebar) is a React component."),
        ("React DOM", "Renders React components into the browser DOM. Used in main.jsx to mount the app."),
        ("Vite 6", "Fast build tool and development server. Replaces Create React App. Provides hot module replacement (instant UI updates during development) and proxies /api to backend."),
        ("@vitejs/plugin-react", "Vite plugin that enables React JSX transformation and Fast Refresh."),
        ("Plain CSS", "No Tailwind or Bootstrap — custom dark theme CSS in index.css inspired by ChatGPT UI."),
        ("localStorage (browser API)", "Stores JWT token, user info, chat history, and suggestion tracking per user in the browser."),
        ("fetch API (browser)", "Native browser HTTP client used in api.js to call backend endpoints."),
        ("crypto.randomUUID() (browser)", "Generates unique IDs for chat conversations."),
    ]
    add_table(doc, ["Library/API", "Purpose & Usage in This Project"], frontend_libs)

    add_heading(doc, "4.3 External Services", 2)
    external = [
        ("Gmail SMTP", "Sends OTP verification emails. Requires Gmail account with 2FA and App Password. Configured via SMTP_USER and SMTP_PASSWORD in .env."),
        ("Hugging Face Hub", "Hosts the BGE-M3 embedding model. Downloaded automatically on first backend startup (~2GB, one-time download)."),
    ]
    add_table(doc, ["Service", "Purpose"], external)

    # 5. SEMANTIC SEARCH
    add_heading(doc, "5. How Semantic Search Works", 1)
    add_para(doc, "Step-by-step process when user asks a question:", bold=True)
    steps = [
        "User types: 'What is the price of Hyundai Creta?' in the chat input.",
        "Frontend sends POST /chat with the message to the backend.",
        "Backend checks if message is a slot availability query (slot_intent.py). If yes, returns booking slots instead.",
        "For FAQ queries: chroma_db.py calls embed_query() to convert the question into a 1024-dimension vector using BGE-M3 model.",
        "ChromaDB searches all stored FAQ vectors using cosine similarity (HNSW index).",
        "ChromaDB returns the closest FAQ match and a distance score.",
        "Distance is converted to similarity: similarity = 1 - distance.",
        "If similarity >= 0.55 (SIMILARITY_THRESHOLD), the stored answer from Excel is returned.",
        "If similarity < 0.55, returns 'Sorry, no data found.' — no answer is fabricated.",
        "suggestions.py generates contextual follow-up chips based on the question topic.",
        "chat_log_service.py saves the query, answer, and user info to database for admin monitoring.",
        "Response sent back to frontend and displayed in MessageBubble component.",
    ]
    for i, s in enumerate(steps, 1):
        add_numbered(doc, s)

    add_para(doc, "")
    add_para(doc, "FAQ Ingestion (Startup Process):", bold=True)
    ingest = [
        "On backend startup, data_loader.py reads hyundai_faq.xlsx (99 FAQ pairs).",
        "Computes hash of Excel file to detect changes.",
        "If Excel changed or ChromaDB empty, re-ingests all FAQs.",
        "embed_texts() converts all questions to vectors using BGE-M3.",
        "Vectors stored in ChromaDB with metadata (question + answer text).",
        "ingestion_meta.json records hash, count, model name, timestamp.",
        "If nothing changed, skips re-ingestion for fast startup.",
    ]
    for s in ingest:
        add_bullet(doc, s)

    add_para(doc, "")
    add_para(doc, "Why NOT use ChatGPT/LLM?", bold=True)
    add_para(
        doc,
        "This is intentional. LLMs can hallucinate (make up false information). For a car showroom, "
        "wrong price or mileage information is dangerous. Retrieval-based approach guarantees every "
        "answer comes from verified FAQ data only.",
    )

    # 6. DATABASE
    add_heading(doc, "6. Database Design (SQLite)", 1)
    add_para(doc, "Database file: backend/app.db (SQLite — lightweight, file-based, no separate server needed)", bold=True)
    add_para(doc, "")
    add_table(
        doc,
        ["Table", "Columns", "Purpose"],
        [
            ("users", "id (UUID), email, password_hash, full_name, created_at", "Registered user accounts. Password stored as bcrypt hash, never plain text."),
            ("bookings", "id, user_id (FK), booking_date, time_slot, vehicle_model, status, created_at", "Test drive bookings. Unique constraint on (date + time_slot) prevents double booking."),
            ("otp_codes", "id, email, code (6-digit), purpose, expires_at, used, created_at", "Temporary OTP codes for login, registration, password reset. Expire in 10 minutes."),
            ("chat_logs", "id, user_id (FK nullable), user_email, user_name, query, answer, found, response_type, created_at", "Every chat interaction logged for admin monitoring."),
        ],
    )

    # 7. API ENDPOINTS
    add_heading(doc, "7. API Endpoints (Complete List)", 1)

    add_heading(doc, "7.1 Core Endpoints (app.py)", 2)
    add_table(
        doc,
        ["Method", "Endpoint", "Description", "Auth Required"],
        [
            ("GET", "/health", "Backend health check and KB status", "No"),
            ("GET", "/stats", "FAQ count, ChromaDB stats, embedding model info", "No"),
            ("POST", "/chat", "Main chat — FAQ search or slot availability", "Optional (logs user if logged in)"),
        ],
    )

    add_heading(doc, "7.2 Authentication (/auth)", 2)
    add_table(
        doc,
        ["Method", "Endpoint", "Description"],
        [
            ("POST", "/auth/register", "Create account, send email OTP"),
            ("POST", "/auth/verify-register-otp", "Verify registration OTP, return JWT"),
            ("POST", "/auth/login", "Login with email/password, send OTP for 2FA"),
            ("POST", "/auth/verify-login-otp", "Verify login OTP, return JWT"),
            ("POST", "/auth/admin-login", "Admin login (bypasses OTP)"),
            ("POST", "/auth/forgot-password", "Send password reset OTP to email"),
            ("POST", "/auth/reset-password", "Reset password with OTP"),
            ("GET", "/auth/me", "Get current logged-in user profile"),
        ],
    )

    add_heading(doc, "7.3 Bookings (/bookings)", 2)
    add_table(
        doc,
        ["Method", "Endpoint", "Description", "Auth"],
        [
            ("GET", "/bookings/dates", "List bookable dates (next 14 days)", "No"),
            ("GET", "/bookings/slots?date=", "Slots for a date with taken/available status", "No"),
            ("GET", "/bookings/next-available", "Next N free slots across all dates", "No"),
            ("GET", "/bookings/my", "Current user's bookings", "Yes (JWT)"),
            ("POST", "/bookings", "Book a test drive slot", "Yes (JWT)"),
        ],
    )

    add_heading(doc, "7.4 Admin (/admin) — All require admin JWT", 2)
    add_table(
        doc,
        ["Method", "Endpoint", "Description"],
        [
            ("GET", "/admin/bookings", "List all bookings"),
            ("POST", "/admin/bookings", "Create booking for any customer"),
            ("PUT", "/admin/bookings/{id}", "Update a booking"),
            ("DELETE", "/admin/bookings/{id}", "Delete a booking"),
            ("GET", "/admin/dates", "Available booking dates"),
            ("GET", "/admin/slots?date=", "Slot overview for admin"),
            ("GET", "/admin/chat-logs", "Monitor all user queries and responses"),
        ],
    )

    # 8. AUTH
    add_heading(doc, "8. Authentication & Security", 1)
    add_para(doc, "Registration Flow:", bold=True)
    for s in [
        "User fills email, password, name in AuthModal.",
        "POST /auth/register creates user with bcrypt-hashed password.",
        "6-digit OTP generated, saved to otp_codes table.",
        "Professional HTML email sent via Gmail SMTP.",
        "User enters OTP → POST /auth/verify-register-otp.",
        "JWT token returned and stored in browser localStorage.",
    ]:
        add_numbered(doc, s)

    add_para(doc, "")
    add_para(doc, "Login Flow (2FA):", bold=True)
    for s in [
        "User enters email + password.",
        "Backend verifies bcrypt password hash.",
        "OTP sent to email (not shown on screen — security).",
        "User enters OTP from email.",
        "JWT token issued on successful verification.",
    ]:
        add_numbered(doc, s)

    add_para(doc, "")
    add_para(doc, "JWT Token Contents:", bold=True)
    add_bullet(doc, "sub — User ID")
    add_bullet(doc, "email — User email")
    add_bullet(doc, "role — 'user' or 'admin'")
    add_bullet(doc, "exp — Expiry timestamp (default 24 hours)")
    add_para(doc, "")
    add_para(doc, "Token sent in header: Authorization: Bearer <token>", bold=True)

    # 9. EMAIL
    add_heading(doc, "9. Email OTP System (SMTP)", 1)
    add_para(
        doc,
        "OTP emails are sent using Gmail SMTP. The email_service.py module builds professional "
        "HTML emails with Hyundai branding, individual digit boxes for the 6-digit code, and "
        "purpose-specific messages (login, registration, password reset).",
    )
    add_para(doc, "SMTP Configuration (.env):", bold=True)
    add_bullet(doc, "SMTP_HOST=smtp.gmail.com")
    add_bullet(doc, "SMTP_PORT=587 (STARTTLS)")
    add_bullet(doc, "SMTP_USER=your Gmail address (login + sender)")
    add_bullet(doc, "SMTP_PASSWORD=Gmail App Password (16 characters, NOT regular password)")
    add_para(doc, "")
    add_para(doc, "OTP Security:", bold=True)
    add_bullet(doc, "OTP expires in 10 minutes")
    add_bullet(doc, "OTP is single-use (marked as used after verification)")
    add_bullet(doc, "Old OTPs invalidated when new one is generated")
    add_bullet(doc, "OTP never returned to frontend API — only sent via email")

    # 10. BOOKING
    add_heading(doc, "10. Test Drive Booking System", 1)
    add_para(doc, "Slot Configuration:", bold=True)
    add_bullet(doc, "Operating hours: 10:00 AM to 8:00 PM (10 slots per day)")
    add_bullet(doc, "Each slot is 1 hour (e.g., 10:00-11:00, 11:00-12:00)")
    add_bullet(doc, "Bookable up to 14 days in advance")
    add_bullet(doc, "Unique constraint: only one booking per date+time_slot")
    add_para(doc, "")
    add_para(doc, "Conflict Handling:", bold=True)
    add_para(doc, "If user tries to book a taken slot, backend returns HTTP error with message and suggests the next available slot.")
    add_para(doc, "")
    add_para(doc, "In-Chat Slot Display:", bold=True)
    add_para(doc, "When user asks 'available timings for today', slot_intent.py detects the intent and booking_service.py returns next 5 free slots displayed in SlotTable.jsx component with Book buttons.")

    # 11. ADMIN
    add_heading(doc, "11. Admin Dashboard", 1)
    add_para(doc, "Admin users see AdminDashboard.jsx instead of ChatPage. Features:", bold=True)
    for f in [
        "View all test drive bookings in a table",
        "Create, edit, delete bookings for any customer",
        "View slot availability for any date",
        "Chat Monitor — see every user query, bot response, timestamp, user email",
        "Filter and manage booking status (confirmed, etc.)",
    ]:
        add_bullet(doc, f)

    # 12. FRONTEND
    add_heading(doc, "12. Frontend Structure", 1)
    add_para(doc, "Entry: index.html → main.jsx → App.jsx", bold=True)
    add_para(doc, "App.jsx checks AuthContext — if user.is_admin, show AdminDashboard, else ChatPage.", bold=False)
    add_para(doc, "")
    add_para(doc, "ChatPage.jsx orchestrates:", bold=True)
    for c in [
        "Sidebar — conversation history, navigation",
        "Header — title, sign in/out, my bookings",
        "ChatArea — messages, welcome screen, suggestions, slot table",
        "ChatInput — user text input",
        "AuthModal — login/register/OTP/password reset",
        "BookingModal — date and slot picker",
        "KnowledgePanel — FAQ/ChromaDB statistics",
        "useChatHistory hook — per-user localStorage sessions",
        "useSuggestionTracker hook — tracks clicked suggestion chips",
    ]:
        add_bullet(doc, c)

    # 13. EVERY FILE
    add_heading(doc, "13. Every File Explained", 1)

    add_heading(doc, "Root Files", 2)
    root_files = [
        ("README.md", "Project readme with setup instructions"),
        (".gitignore", "Excludes secrets, database, vector DB from git"),
        ("start_backend.bat / .ps1", "Start Python backend on port 8000"),
        ("start_frontend.bat / .ps1", "Start React dev server on port 5173"),
        ("stop_servers.bat / .ps1", "Kill processes on ports 8000 and 5173"),
        ("data/hyundai_faq.xlsx", "Source FAQ data — 99 Question/Answer pairs"),
    ]
    add_table(doc, ["File", "Purpose"], root_files)

    add_heading(doc, "Backend Files", 2)
    backend_files = [
        ("app.py", "MAIN ENTRY — FastAPI app, /chat, /health, /stats, router mounting, startup lifespan"),
        ("config.py", "Loads .env, defines all paths and settings"),
        ("database.py", "SQLite engine, session factory, init_db()"),
        ("models.py", "SQLAlchemy models: User, Booking, OtpRecord, ChatLog"),
        (".env", "Secrets — SMTP, JWT (NOT committed to git)"),
        (".env.example", "Template for environment variables"),
        ("requirements.txt", "Python package dependencies"),
        ("test_smtp.py", "Utility to test Gmail SMTP connection"),
        ("auth_utils.py", "bcrypt hashing, JWT create/verify, auth dependencies"),
        ("otp_service.py", "Generate, store, send, verify 6-digit OTP"),
        ("email_service.py", "HTML email templates, Gmail SMTP sending"),
        ("booking_service.py", "Slot logic, conflict detection, availability"),
        ("chat_log_service.py", "Save and retrieve chat logs for admin"),
        ("chroma_db.py", "ChromaDB vector store, semantic search, ingestion"),
        ("data_loader.py", "Read Excel FAQs, hash checking, ingestion metadata"),
        ("embeddings.py", "BGE-M3 model loading, embed_texts, embed_query"),
        ("suggestions.py", "Dynamic follow-up suggestion chip logic"),
        ("slot_intent.py", "Detect slot availability queries in chat"),
        ("routers/auth_router.py", "All /auth/* endpoints"),
        ("routers/bookings_router.py", "All /bookings/* endpoints"),
        ("routers/admin_router.py", "All /admin/* endpoints"),
        ("app.db", "SQLite database file (runtime, not in git)"),
        ("chroma_db/", "ChromaDB persistent vector storage (not in git)"),
    ]
    add_table(doc, ["File", "Purpose"], backend_files)

    add_heading(doc, "Frontend Files", 2)
    frontend_files = [
        ("index.html", "HTML page shell"),
        ("vite.config.js", "Vite config + /api proxy to backend"),
        ("package.json", "NPM dependencies and scripts"),
        ("src/main.jsx", "React entry point"),
        ("src/App.jsx", "Root component, admin vs chat routing"),
        ("src/index.css", "Global dark theme styles"),
        ("src/pages/ChatPage.jsx", "Main chat page — orchestrates all chat UI"),
        ("src/pages/AdminDashboard.jsx", "Admin panel — bookings + chat monitor"),
        ("src/contexts/AuthContext.jsx", "Global auth state, JWT in localStorage"),
        ("src/services/api.js", "All HTTP API calls to backend"),
        ("src/hooks/useChatHistory.js", "Per-user chat sessions in localStorage"),
        ("src/hooks/useSuggestionTracker.js", "Track used suggestion chip IDs"),
        ("src/components/Header.jsx", "Top navigation bar"),
        ("src/components/Sidebar.jsx", "Left sidebar — history, links"),
        ("src/components/ChatArea.jsx", "Message list container"),
        ("src/components/ChatInput.jsx", "Text input and send button"),
        ("src/components/MessageBubble.jsx", "Single chat message bubble"),
        ("src/components/WelcomeScreen.jsx", "Empty state welcome message"),
        ("src/components/LoadingIndicator.jsx", "Loading animation during API call"),
        ("src/components/FollowUpSuggestions.jsx", "Clickable suggestion chips"),
        ("src/components/SlotTable.jsx", "Available slots table with Book buttons"),
        ("src/components/AuthModal.jsx", "Login, register, OTP, password modals"),
        ("src/components/BookingModal.jsx", "Test drive booking form"),
        ("src/components/KnowledgePanel.jsx", "FAQ/ChromaDB stats side panel"),
    ]
    add_table(doc, ["File", "Purpose"], frontend_files)

    # 14. ENV VARS
    add_heading(doc, "14. Environment Variables (.env)", 1)
    add_table(
        doc,
        ["Variable", "Description", "Example"],
        [
            ("DEBUG_MODE", "Dev mode flags", "false"),
            ("JWT_SECRET", "Secret key for signing JWT tokens", "long-random-string"),
            ("JWT_EXPIRE_MINUTES", "Token validity in minutes", "1440 (24 hours)"),
            ("SMTP_HOST", "Email server hostname", "smtp.gmail.com"),
            ("SMTP_PORT", "Email server port", "587"),
            ("SMTP_USER", "Gmail login + sender email", "you@gmail.com"),
            ("SMTP_PASSWORD", "Gmail App Password", "16-char app password"),
            ("COLLECTION_NAME", "ChromaDB collection name", "hyundai_faq"),
            ("EMBEDDING_MODEL", "HuggingFace model name", "BAAI/bge-m3"),
            ("SIMILARITY_THRESHOLD", "Min similarity to return answer", "0.55"),
            ("CORS_ORIGINS", "Allowed frontend URLs", "http://localhost:5173"),
        ],
    )

    # 15. HOW TO RUN
    add_heading(doc, "15. How to Run the Project", 1)
    add_para(doc, "Prerequisites: Python 3.10+, Node.js 18+, hyundai_faq.xlsx in data/ folder", bold=True)
    add_para(doc, "")
    add_para(doc, "Step 1 — Backend:", bold=True)
    add_numbered(doc, "cd backend")
    add_numbered(doc, "pip install -r requirements.txt")
    add_numbered(doc, "Copy .env.example to .env and fill SMTP credentials")
    add_numbered(doc, "python -m uvicorn app:app --port 8000")
    add_numbered(doc, "Wait for 'Knowledge base ready' (first run downloads BGE-M3 model ~2GB)")
    add_para(doc, "")
    add_para(doc, "Step 2 — Frontend:", bold=True)
    add_numbered(doc, "cd frontend")
    add_numbered(doc, "npm install")
    add_numbered(doc, "npm run dev")
    add_numbered(doc, "Open http://localhost:5173 in browser")

    # 16. DATA FLOW
    add_heading(doc, "16. Data Flow Diagrams (Text)", 1)
    add_para(doc, "Chat Message Flow:", bold=True)
    add_para(
        doc,
        "User Input → ChatPage.jsx → api.js (POST /api/chat) → vite proxy → app.py /chat "
        "→ slot_intent OR chroma_db.search → suggestions.py → chat_log_service → JSON response "
        "→ MessageBubble.jsx + FollowUpSuggestions.jsx",
    )
    add_para(doc, "")
    add_para(doc, "Login Flow:", bold=True)
    add_para(
        doc,
        "AuthModal → api.js → auth_router → otp_service → email_service → Gmail → User inbox "
        "→ User enters OTP → verify → JWT → AuthContext → localStorage",
    )

    # 17. VIVA Q&A
    add_heading(doc, "17. Common Viva Questions & Answers", 1)
    viva = [
        ("What type of chatbot is this?", "Retrieval-based (not generative). Answers come only from stored FAQ data via semantic search. No LLM generation."),
        ("What is semantic search?", "Search based on meaning, not exact keywords. 'Creta price' and 'cost of Hyundai Creta' map to similar vectors and find the same FAQ."),
        ("What is an embedding?", "A numerical vector (list of numbers) representing the meaning of text. Similar meanings produce similar vectors."),
        ("Why ChromaDB?", "Specialized vector database optimized for fast similarity search among millions of vectors. Stores embeddings persistently on disk."),
        ("What is cosine similarity?", "Measures angle between two vectors. Value 1 = identical meaning, 0 = unrelated. We use threshold 0.55."),
        ("Why BGE-M3 over MiniLM?", "BGE-M3 is newer, larger, and more accurate for semantic search especially with varied phrasing."),
        ("What is JWT?", "JSON Web Token — a signed token proving user identity. Sent in Authorization header. Stateless authentication."),
        ("Why bcrypt for passwords?", "One-way hashing — even if database is stolen, passwords cannot be reversed."),
        ("What is 2FA OTP?", "Two-Factor Authentication — password + email OTP. Even if password is stolen, attacker needs access to email."),
        ("What is FastAPI?", "Modern Python API framework with automatic validation, docs, and async support."),
        ("What is SQLAlchemy ORM?", "Maps Python classes to database tables so we write Python instead of SQL."),
        ("What is CORS?", "Cross-Origin Resource Sharing. Browser security. Vite proxy avoids CORS in development."),
        ("What is Vite proxy?", "Forwards /api requests from port 5173 to port 8000 so frontend and backend appear same-origin."),
        ("How are bookings prevented from double-booking?", "Unique constraint on (booking_date + time_slot) in SQLite. Backend checks before insert."),
        ("What happens if no FAQ matches?", "Returns 'Sorry, no data found.' — system does not invent an answer."),
        ("Where is chat history stored?", "Browser localStorage per user ID. Backend chat_logs table for admin monitoring."),
        ("What is similarity threshold 0.55?", "Configurable in .env. Lower = more permissive matches. Higher = stricter. 0.55 balances accuracy and recall."),
    ]
    add_table(doc, ["Question", "Answer"], viva)

    # 18. LIMITATIONS
    add_heading(doc, "18. Limitations & Future Scope", 1)
    add_para(doc, "Current Limitations:", bold=True)
    for l in [
        "Answers limited to FAQ Excel content — cannot answer questions outside knowledge base",
        "Single language (English) for FAQ content",
        "Gmail SMTP has daily sending limits for personal accounts",
        "SQLite not ideal for very high concurrent users (production would use PostgreSQL)",
        "Embeddings model requires ~2GB download on first run",
        "No real-time websocket — uses request/response HTTP",
    ]:
        add_bullet(doc, l)
    add_para(doc, "")
    add_para(doc, "Future Scope:", bold=True)
    for f in [
        "Add more languages (Hindi FAQ support)",
        "Deploy to cloud (AWS/Azure) with PostgreSQL",
        "Add voice input/output",
        "Integrate live Hyundai API for real-time prices",
        "Add analytics dashboard for popular questions",
        "Use Redis for OTP caching and session management",
        "Add rate limiting to prevent OTP abuse",
    ]:
        add_bullet(doc, f)

    # 19. SECURITY
    add_heading(doc, "19. Security Notes Before GitHub", 1)
    for s in [
        "Never commit backend/.env — contains SMTP password and JWT secret",
        "Never commit backend/app.db — contains user data",
        "Admin passwords are currently hardcoded in source — move to .env before public repo",
        "Regenerate Gmail App Password if ever exposed",
        "Change JWT_SECRET in production",
        ".gitignore already excludes .env, app.db, chroma_db/",
    ]:
        add_bullet(doc, s)

    # Footer
    doc.add_page_break()
    end = doc.add_paragraph()
    end.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = end.add_run("— End of Document —\nHyundai Knowledge Assistant v2.1.0")
    r.font.size = Pt(12)
    r.font.color.rgb = RGBColor(0, 44, 95)

    return doc


if __name__ == "__main__":
    document = build_document()
    document.save(OUTPUT)
    print(f"Documentation saved to: {OUTPUT}")
