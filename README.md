# ⚡ GitHub AI Assistant

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/LLM-Groq%20120B-f55036)](https://groq.com)
[![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-blue)](https://trychroma.com)
[![React](https://img.shields.io/badge/Frontend-React%2018-61dafb?logo=react&logoColor=black)](https://react.dev)

An enterprise-grade, autonomous AI assistant capable of understanding GitHub repositories, indexing codebases with RAG & vector embeddings, explaining files, detecting security vulnerabilities & bugs, generating unit tests, analyzing issues/PRs, and drafting complete documentation.

---

## 🚀 Key Features

- 🔍 **Understand Repositories**: Connects directly to GitHub via REST API to inspect branches, file trees, commit logs, and issues.
- 🧠 **ChromaDB RAG Pipeline**: Chunks code, creates dense embeddings, and stores them in ChromaDB for high-precision semantic code retrieval.
- 💬 **Context-Aware AI Chat**: Converse with your repository using ultra-fast Groq LLM inference (`openai/gpt-oss-120b`). Cites exact file lines.
- 🐛 **Bug & Security Auditing**: 1-click static analysis to detect null errors, race conditions, memory leaks, and boundary bugs with ready-to-paste fixes.
- 🧪 **Automated Test Generation**: Generates comprehensive unit tests covering edge cases and mocks for any selected source code file.
- 📝 **README & Architecture Generator**: Synthesizes repository structure into production READMEs and Mermaid component diagrams.
- 🔀 **Issue & PR Diagnosis**: Analyzes open/closed GitHub issues and PRs, correlates with repository code, and proposes solutions.
- 🎨 **Dual-Mode UI**:
  1. **Instant Web App**: Served directly by FastAPI at `http://127.0.0.1:8000` with zero Node.js dependencies.
  2. **Modular Vite React**: Located in `frontend/` running on `http://localhost:5000` (proxied to FastAPI backend).

---

## 📂 Project Architecture

```
github-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI Application & Routes mounting
│   │   ├── config.py                # Environment configuration
│   │   ├── api/                     # REST API Endpoints
│   │   │   ├── auth.py              # PAT validation & rate limits
│   │   │   ├── github.py            # Repositories, tree, file contents, issues, commits
│   │   │   ├── repository.py        # ChromaDB indexing & status
│   │   │   ├── chat.py              # RAG chat & streaming
│   │   │   └── tools.py             # Code actions & doc generation
│   │   ├── agents/                  # Multi-Agent Logic
│   │   │   ├── code_agent.py        # Code explanation, bug finding, tests
│   │   │   ├── documentation_agent.py # README & Architecture generator
│   │   │   └── github_agent.py      # Core RAG assistant & issue analyzer
│   │   ├── rag/                     # Retrieval-Augmented Generation
│   │   │   ├── loader.py            # Code file filtering & retrieval
│   │   │   ├── chunker.py           # Syntax-aware overlapping chunker
│   │   │   ├── embeddings.py        # Embedding functions (OpenAI / Fast dense)
│   │   │   └── vectorstore.py       # ChromaDB Persistent Client & Collection manager
│   │   ├── services/
│   │   │   ├── github_service.py    # GitHub REST API client
│   │   │   └── llm_service.py       # Groq client with streaming & fallback
│   │   ├── models/
│   │   │   └── schemas.py           # Pydantic data contracts
│   │   └── static/                  # Rich Glassmorphism Web App
│   │       ├── index.html
│   │       ├── style.css
│   │       └── app.js
│   ├── requirements.txt
│   └── .env
├── frontend/                        # Modular Vite React Application
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── index.css
│   │   └── services/api.js
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── run.bat                          # Windows 1-click launcher
├── README.md
└── .gitignore
```

---

## ⚡ Quick Start

### 1. Launch the Backend & Web App

You can double-click **`run.bat`**, or run from PowerShell/Terminal:

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open your browser at:
👉 **FastAPI Backend / App**: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**
👉 **React Frontend (Vite)**: **[http://localhost:5000](http://localhost:5000)** (`run_frontend.bat` or `cd frontend && npm run dev`)

### 2. Configure Environment (`backend/.env`)

The `.env` file is pre-configured with your GitHub PAT and Groq API key:

```env
GITHUB_TOKEN=github_pat_xxxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
GROQ_MODEL=openai/gpt-oss-120b
CHROMA_PERSIST_DIRECTORY=./data/chroma_db
```

You can also dynamically adjust settings and switch models anytime from the in-app **Settings (⚙️)** modal.

---

## 🧪 Interactive Walkthrough

1. **Select Repository**: Pick any of your repositories from the dropdown (e.g. `AI-Research-Agent`).
2. **Index with ChromaDB**: Click **"Index with ChromaDB"**. Files are retrieved, chunked, and embedded into local vector storage.
3. **Explore Files**: Browse folders, click any source code file to view syntax-highlighted code.
4. **Run AI Diagnostics**: Click **"🔍 Explain"**, **"🐛 Find Bugs"**, or **"🧪 Tests"** on any file.
5. **Chat with Repository**: Ask natural language questions like *"Where is the entry point?"* or *"Explain how data processing works"*.

---

## 🧩 Injected GitHub Icon (Browser Extension)

You can have the AI Assistant icon injected directly onto `https://github.com` (including your profile `github.com/Jyotir2004` and all repositories):

1. In Google Chrome, Brave, or Edge, go to:
   `chrome://extensions/`
2. Toggle on **Developer mode** (top right switch).
3. Click **"Load unpacked"**.
4. Select the `extension/` folder inside this project directory:
   `c:\Users\dell\OneDrive\Desktop\Github assistant\extension`
5. Visit [github.com/Jyotir2004](https://github.com/Jyotir2004) or any repository.
6. Look at the bottom-right corner of the page: you will see the **⚡ AI Assistant** floating icon and an **"⚡ AI Copilot"** button in GitHub's header! Click it to chat, explain files, and find bugs directly on GitHub!

