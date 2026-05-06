# RAG Chatbot — Conversation Intelligence

A full-stack RAG (Retrieval-Augmented Generation) chatbot that analyses conversation datasets.

## Stack
- **Frontend**: React 18 + Vite 5 (dark glassmorphism UI)
- **Backend**: Python Django 5 + Django REST Framework
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`) + FAISS
- **Topic Detection**: TF-IDF cosine similarity (scikit-learn)
- **No paid API required** — fully local

---

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

Backend runs at **http://localhost:8000**

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

### 3. Process Data

1. Open **http://localhost:5173** in your browser
2. Click **"⚡ Process Conversations"**
3. Wait 5–15 minutes while the system:
   - Parses all messages from `conversations.csv`
   - Detects topic changes
   - Builds FAISS embeddings index
   - Extracts user persona
4. Chat, explore topics and persona!

---

## How It Works

### Topic Detection
Messages are processed chronologically. A sliding window of 15 messages is
compared against the next window using TF-IDF vectors and cosine similarity.
When similarity drops below **0.25**, a new topic checkpoint is created.
Each checkpoint stores an extractive summary (TextRank) and top keywords.

### 100-Message Checkpoints
Every 100 messages (regardless of topic), a checkpoint summary is generated.
These provide a chronological overview independent of topic segmentation.

### Retrieval
When you ask a question:
1. **Semantic search** — query is embedded with sentence-transformers and
   searched against the FAISS index of all message chunks
2. **Keyword search** — TF-IDF cosine similarity against all topic summaries
3. Results are merged and used to generate an answer

### Persona Extraction
Rule-based NLP pattern matching on all messages:
- **Habits**: food mentions, exercise, routines
- **Personal facts**: occupations, pets, family, locations, books
- **Personality**: positivity ratio, humor patterns, empathy signals
- **Communication style**: avg message length, formality, emoji usage

### Optional: Better Answers with Groq
Create a `.env` file in `backend/` with:
```
GROQ_API_KEY=your_key_here
```
Get a free key at https://console.groq.com — enables Llama 3 answers.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/process/` | Start background processing |
| GET | `/api/status/` | Processing status + progress |
| POST | `/api/chat/` | Ask a question |
| GET | `/api/persona/` | Get persona JSON |
| GET | `/api/topics/` | Topic checkpoints (paginated) |
| GET | `/api/checkpoints/` | 100-msg checkpoints (paginated) |
| GET | `/api/stats/` | Overall counts |

---

## Project Structure

```
rag-chatbot/
├── conversations.csv          ← Dataset (untouched)
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── ragchatbot/            ← Django settings
│   └── api/
│       ├── models.py
│       ├── views.py
│       ├── urls.py
│       ├── pipeline.py        ← Background processing
│       ├── rag_engine/
│       │   ├── preprocessor.py
│       │   ├── topic_detector.py
│       │   ├── summarizer.py
│       │   ├── embedder.py
│       │   └── retriever.py
│       └── persona/
│           ├── extractor.py
│           └── store.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── index.css
        ├── api/client.js
        └── components/
            ├── Navbar.jsx
            ├── ChatWindow.jsx
            ├── PersonaPanel.jsx
            └── TopicsPanel.jsx
```
