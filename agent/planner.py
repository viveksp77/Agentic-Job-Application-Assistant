from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# The tool execution order is always the same — no need to call an LLM for this.
# Each step declares exactly which context keys it needs so the executor
# can validate before calling the tool.
PLAN: List[Dict[str, Any]] = [
    {
        'tool_name': 'parse_resume',
        'description': 'Extract text from uploaded resume PDF',
        'requires': [],
        'provides': ['resume_text'],
    },
    {
        'tool_name': 'analyze_job_description',
        'description': 'Extract title, skills, and requirements from JD',
        'requires': [],
        'provides': ['jd_analysis', 'job_skills'],
    },
    {
        'tool_name': 'extract_resume_skills',
        'description': 'Identify skills present in the resume',
        'requires': ['resume_text'],
        'provides': ['resume_skills'],
    },
    {
        'tool_name': 'skill_gap_analysis',
        'description': 'Compare resume skills vs job skills and compute ATS score',
        'requires': ['resume_skills', 'job_skills'],
        'provides': ['gap_analysis', 'ats_score', 'missing_skills'],
    },
    {
        'tool_name': 'optimize_resume',
        'description': 'Rewrite resume bullets to match job requirements',
        'requires': ['resume_text', 'job_skills'],
        'provides': ['optimized_resume'],
    },
    {
        'tool_name': 'generate_cover_letter',
        'description': 'Create a tailored cover letter for the role',
        'requires': ['jd_analysis', 'resume_text', 'resume_skills', 'missing_skills'],
        'provides': ['cover_letter'],
    },
    {
        'tool_name': 'generate_interview_questions',
        'description': 'Generate targeted interview questions',
        'requires': ['resume_skills'],
        'provides': ['interview_questions'],
    },
    {
        'tool_name': 'skill_improvement_suggestions',
        'description': 'Suggest learning resources for skill gaps',
        'requires': ['missing_skills'],
        'provides': ['skill_suggestions'],
    },
]


def create_plan(resume_path: str, job_desc: str) -> List[Dict[str, Any]]:
    """
    Return the fixed execution plan.

    The plan is deterministic — the 8-step sequence is always the same regardless
    of the resume or job description. Calling an LLM here adds latency without
    any benefit. If you later need dynamic planning (e.g. skipping steps based
    on user preferences), add that logic here as conditional filtering.

    Args:
        resume_path: Path to the uploaded PDF (kept for signature compatibility).
        job_desc:    Raw job description text (kept for signature compatibility).

    Returns:
        Ordered list of step dicts consumed by execute_plan().
    """
    logger.info("Creating execution plan (%d steps)", len(PLAN))
    return PLAN.copy()


def get_plan_summary() -> List[str]:
    """Return human-readable step descriptions for the UI progress display."""
    return [f"{i+1}. {step['description']}" for i, step in enumerate(PLAN)]