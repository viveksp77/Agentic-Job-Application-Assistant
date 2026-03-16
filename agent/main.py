from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import tempfile
import os
import re
import json

from agent.planner import create_plan
from agent.executor import execute_plan
from agent.memory import AgentMemory
from agent.evaluator import evaluate_resume_match
from utils.llm_client import llm_client

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Resume analysis endpoint
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# History endpoint
# ---------------------------------------------------------------------------

@app.get("/history")
async def history():
    from database.db_manager import get_applications
    return get_applications()


# ---------------------------------------------------------------------------
# Interview simulator models
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


# ---------------------------------------------------------------------------
# Interview endpoints
# ---------------------------------------------------------------------------

@app.post("/interview/question")
async def get_interview_question(req: InterviewRequest):
    """Generate the next interview question based on conversation history."""
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a strict but fair technical interviewer for a {req.job_role} role. "
                f"Difficulty level: {req.difficulty}. "
                f"Ask ONE clear, specific interview question relevant to the role. "
                f"No preamble, no numbering, no explanation — just the question itself."
            )
        }
    ] + [
        {"role": m.role, "content": m.content}
        for m in req.conversation
    ] + [
        {
            "role": "user",
            "content": (
                f"Ask me interview question number {req.question_number} "
                f"for a {req.job_role} position at {req.difficulty} difficulty."
            )
        }
    ]

    response = llm_client.chat(messages=messages)
    return {"question": response.strip()}


@app.post("/interview/evaluate")
async def evaluate_answer(req: InterviewRequest):
    """Score the user's answer and provide structured feedback."""
    last_question = req.conversation[-1].content if req.conversation else "N/A"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a technical interviewer evaluating a candidate's answer. "
                "Return ONLY valid JSON in this exact format with no extra text:\n"
                '{"clarity": 7, "relevance": 8, "depth": 6, '
                '"feedback": "Good explanation but missing specific examples.", '
                '"strength": "Clear communication style", '
                '"improvement": "Add concrete examples from past projects"}'
            )
        },
        {
            "role": "user",
            "content": (
                f"Job role: {req.job_role}\n"
                f"Difficulty: {req.difficulty}\n"
                f"Interview question: {last_question}\n"
                f"Candidate's answer: {req.user_answer}\n\n"
                "Score this answer on:\n"
                "- clarity (1-10): how clear and well-structured the answer is\n"
                "- relevance (1-10): how relevant it is to the question\n"
                "- depth (1-10): technical depth and detail\n"
                "Also provide: feedback (1 sentence), strength (1 phrase), improvement (1 phrase)."
            )
        }
    ]

    response = llm_client.chat(messages=messages)

    # Parse JSON from response
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            # Ensure all required keys exist
            return {
                "clarity":     int(data.get("clarity", 7)),
                "relevance":   int(data.get("relevance", 7)),
                "depth":       int(data.get("depth", 7)),
                "feedback":    data.get("feedback", "Answer received."),
                "strength":    data.get("strength", "Good attempt."),
                "improvement": data.get("improvement", "Keep practising."),
            }
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback if JSON parsing fails
    return {
        "clarity": 7,
        "relevance": 7,
        "depth": 7,
        "feedback": response[:200] if response else "Answer received.",
        "strength": "Answer submitted successfully.",
        "improvement": "Try to be more specific and structured.",
    }