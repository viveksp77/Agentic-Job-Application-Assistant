# JobAgent AI — Agentic Job Application Assistant

A full-stack AI-powered career tool that analyses your resume against a job description, optimises your application, and prepares you for interviews — automatically.

---

## Demo

| Feature | Description |
|---|---|
| Resume Analysis | Upload a PDF resume and paste a job description — the agent handles everything |
| ATS Scoring | Semantic skill matching using FAISS + sentence embeddings |
| Resume Optimisation | AI-rewritten bullet points tailored to the job |
| Cover Letter | Personalised 3-paragraph cover letter generated in seconds |
| Interview Prep | 10 targeted questions (technical, behavioral, situational) |
| Skill Roadmap | Learning plan with courses and time estimates for missing skills |
| Mock Interview | Live AI interviewer — asks questions, scores answers, gives feedback |
| Application History | SQLite-backed history of all past analyses |

---

## Tech Stack

### Frontend
- **React** (Create React App)
- **Axios** for API calls
- Custom CSS with CSS variables (dark theme)

### Backend (Node.js)
- **Express.js** — REST API middleware
- **Multer** — PDF file upload handling
- Proxies requests to the Python agent

### AI Agent (Python)
- **FastAPI** — Python REST API
- **Ollama** — local LLM inference (`llama3.2`)
- **FAISS** — vector similarity search for semantic skill matching
- **sentence-transformers** — `all-MiniLM-L6-v2` embeddings
- **PyPDF2** — resume PDF parsing
- **SQLite** — application history storage

### Architecture

```
React (localhost:3000)
    ↓ REST
Node.js / Express (localhost:5000)
    ↓ HTTP
Python / FastAPI (localhost:8000)
    ↓
Agent Pipeline (Planner → Executor → Tools → Memory → Evaluator)
    ↓
Ollama (llama3.2) + FAISS
```

---

## Agent Pipeline

The system uses a **Planner–Executor architecture**:

```
1. parse_resume           — extract text from PDF
2. analyze_job_description — extract title, skills, requirements
3. extract_resume_skills  — identify skills in resume
4. skill_gap_analysis     — FAISS semantic comparison
5. optimize_resume        — rewrite bullets with job keywords
6. generate_cover_letter  — personalised 3-paragraph letter
7. generate_interview_questions — 10 targeted questions
8. skill_improvement_suggestions — learning roadmap
```

Each tool is independent and fault-tolerant — if one fails, the pipeline continues and surfaces the error in the UI.

---

## Project Structure

```
job-agent/
├── agent/
│   ├── main.py          # FastAPI app + endpoints
│   ├── planner.py       # Deterministic execution plan
│   ├── executor.py      # Sequential tool runner with context passing
│   ├── tools.py         # All 8 agent tools
│   ├── memory.py        # Step tracking + DB persistence
│   └── evaluator.py     # Resume-job match evaluation
├── utils/
│   ├── llm_client.py    # OpenAI → Ollama → dummy fallback chain
│   ├── skill_extractor.py  # FAISS semantic skill matching
│   └── pdf_parser.py    # PyPDF2 resume parser
├── database/
│   └── db_manager.py    # SQLite CRUD operations
├── prompts/
│   ├── cover_letter_prompt.txt
│   └── resume_optimizer.txt
├── backend/
│   └── server.js        # Node.js Express middleware
└── frontend/
    └── src/
        ├── api/agent.js
        ├── pages/
        │   ├── HomePage.js
        │   ├── InterviewPage.js
        │   └── HistoryPage.js
        └── components/
            ├── ProgressBar.js
            └── ResultTabs.js
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- Node.js 22+
- [Ollama](https://ollama.com/download) installed and running

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/job-agent.git
cd job-agent
```

### 2. Python environment

```bash
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

### 3. Pull the LLM model

```bash
ollama pull llama3.2
```

### 4. Node.js backend

```bash
cd backend
npm install
```

### 5. React frontend

```bash
cd frontend
npm install
```

### 6. Environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=        # Optional — leave blank to use Ollama only
```

---

## Running the App

Open **three terminals**:

**Terminal 1 — Python agent**
```bash
cd job-agent
.\venv\Scripts\activate
uvicorn agent.main:app --reload --port 8000
```

**Terminal 2 — Node.js backend**
```bash
cd job-agent/backend
node server.js
```

**Terminal 3 — React frontend**
```bash
cd job-agent/frontend
npm start
```

Open [http://localhost:3000](http://localhost:3000)

---

## Requirements

```
fastapi
uvicorn
python-multipart
PyPDF2
python-dotenv
openai
ollama
faiss-cpu
sentence-transformers
pandas
```

---

## Key Design Decisions

**Why local LLM (Ollama)?**
Resumes contain sensitive personal data. Running inference locally ensures nothing leaves the user's machine. The architecture supports OpenAI as a drop-in upgrade via the fallback chain in `llm_client.py`.

**Why FAISS for skill matching?**
Keyword matching fails for semantically equivalent terms ("ML" vs "Machine Learning", "NLP" vs "Natural Language Processing"). FAISS with sentence embeddings matches by meaning, not string equality, producing more accurate ATS scores.

**Why deterministic planner?**
The 8-step pipeline is always the same. Using an LLM to generate the plan adds 5–10 seconds of latency with zero benefit. The `planner.py` returns a fixed ordered list — fast, predictable, debuggable.

**Why Node.js middleware?**
Separating the file upload layer (Node/Multer) from the AI logic (Python/FastAPI) keeps concerns clean and makes each service independently replaceable.

---

## Future Enhancements

- [ ] Job scraper (LinkedIn / Indeed URL → auto-fetch job description)
- [ ] Multi-agent parallel execution (resume, analysis, content in parallel)
- [ ] Vector store for cross-session skill memory
- [ ] Resume scoring dashboard with historical trends
- [ ] Export to PDF (cover letter, optimised resume)

---

## License

MIT