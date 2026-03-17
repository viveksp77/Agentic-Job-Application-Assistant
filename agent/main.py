from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import tempfile, os, re, json

from agent.planner import create_plan
from agent.executor import execute_plan
from agent.memory import AgentMemory
from agent.evaluator import evaluate_resume_match
from utils.llm_client import llm_client
from utils.rag_memory import query_resume

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/analyze")
async def analyze(resume: UploadFile = File(...), job_desc: str = Form(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await resume.read())
        resume_path = tmp.name
    try:
        memory = AgentMemory()
        plan = create_plan(resume_path, job_desc)
        results = execute_plan(plan, resume_path, job_desc, memory)
        eval_result = evaluate_resume_match(
            resume_skills=results.get("resume_skills", []),
            job_skills=results.get("job_skills", []),
            ats_score=results.get("ats_score", 0),
            gap_analysis=results.get("gap_analysis"),
        )
        results["evaluation"] = eval_result
        memory.save_to_db(
            resume_path=resume_path,
            job_title=results.get("jd_analysis", {}).get("job_title", "Unknown"),
            ats_score=results.get("ats_score", 0),
        )
        return results
    finally:
        try:
            os.unlink(resume_path)
        except Exception:
            pass


@app.get("/history")
async def history():
    from database.db_manager import get_applications
    return get_applications()


# ---------------------------------------------------------------------------
# Streaming models
# ---------------------------------------------------------------------------

class StreamRequest(BaseModel):
    job_title: str
    job_desc: str
    resume_summary: str
    strengths: str
    missing_skills: List[str]
    resume_id: Optional[str] = None


class InterviewStreamRequest(BaseModel):
    job_desc: str
    resume_skills: List[str]
    resume_id: Optional[str] = None


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------

def _sse_generator(messages: list):
    try:
        for token in llm_client.stream(messages):
            safe = token.replace('\n', '\\n')
            yield f"data: {safe}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"
        yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Streaming endpoints
# ---------------------------------------------------------------------------

@app.post("/stream/cover-letter")
async def stream_cover_letter(req: StreamRequest):
    skills_note = f'Candidate is learning: {", ".join(req.missing_skills[:3])}.' if req.missing_skills else ''
    candidate_context = req.resume_summary
    if req.resume_id:
        exp = query_resume(req.resume_id, "work experience internship responsibilities", n_results=2)
        ach = query_resume(req.resume_id, "achievements awards projects impact results", n_results=2)
        if exp or ach:
            candidate_context = f"{exp}\n\n{ach}".strip()

    messages = [
        {'role': 'system', 'content': 'You are a professional cover letter writer. Return ONLY the letter text — no subject line, no JSON, no markdown.'},
        {'role': 'user', 'content': (
            f'Write a cover letter.\n\nJob Title: {req.job_title}\nJob: {req.job_desc[:600]}\n'
            f'Background:\n{candidate_context[:800]}\nStrengths: {req.strengths}\n{skills_note}\n\n'
            f'P1: Excitement. P2: Two strengths with examples. P3: Call to action. Max 250 words.'
        )}
    ]
    return StreamingResponse(_sse_generator(messages), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/stream/interview-questions")
async def stream_interview_questions(req: InterviewStreamRequest):
    skills_str = ', '.join(req.resume_skills[:10]) if req.resume_skills else 'Not specified'
    bg = query_resume(req.resume_id, "projects experience skills education", n_results=3) if req.resume_id else ''

    messages = [
        {'role': 'system', 'content': 'You are a senior technical interviewer. Return ONLY a numbered list. No preamble.'},
        {'role': 'user', 'content': (
            f'Generate exactly 10 interview questions.\n\nJob: {req.job_desc[:800]}\n'
            f'Skills: {skills_str}\nBackground:\n{bg[:600]}\n\n'
            f'Format:\n1. [question]\n...\n10. [question]\n\nMix: 5 technical, 3 behavioral, 2 situational.'
        )}
    ]
    return StreamingResponse(_sse_generator(messages), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------------------
# Interview simulator
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str
    content: str

class InterviewRequest(BaseModel):
    job_role: str
    difficulty: str
    conversation: List[Message]
    user_answer: Optional[str] = None
    question_number: int = 1

@app.post("/interview/question")
async def get_interview_question(req: InterviewRequest):
    messages = [
        {'role': 'system', 'content': f"You are a strict interviewer for a {req.job_role} role. Difficulty: {req.difficulty}. Ask ONE question — no preamble, no numbering."}
    ] + [{"role": m.role, "content": m.content} for m in req.conversation] + [
        {'role': 'user', 'content': f"Ask interview question {req.question_number} for a {req.job_role} role."}
    ]
    return {"question": llm_client.chat(messages=messages).strip()}

@app.post("/interview/evaluate")
async def evaluate_answer(req: InterviewRequest):
    last_q = req.conversation[-1].content if req.conversation else "N/A"
    messages = [
        {'role': 'system', 'content': 'Evaluate the candidate\'s answer. Return ONLY valid JSON: {"clarity":7,"relevance":8,"depth":6,"feedback":"one sentence","strength":"phrase","improvement":"phrase"}'},
        {'role': 'user', 'content': f"Job: {req.job_role}\nQuestion: {last_q}\nAnswer: {req.user_answer}\n\nScore 1-10 each."}
    ]
    response = llm_client.chat(messages=messages)
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        try:
            d = json.loads(match.group())
            return {"clarity": int(d.get("clarity",7)), "relevance": int(d.get("relevance",7)),
                    "depth": int(d.get("depth",7)), "feedback": d.get("feedback",""),
                    "strength": d.get("strength",""), "improvement": d.get("improvement","")}
        except Exception:
            pass
    return {"clarity":7,"relevance":7,"depth":7,"feedback":response[:200],"strength":"Submitted.","improvement":"Be more specific."}