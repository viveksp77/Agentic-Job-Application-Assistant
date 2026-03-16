import json
import re
from typing import Dict, Any, List

from utils.pdf_parser import parse_resume_pdf
from utils.skill_extractor import extract_skills_from_text, compare_skills
from database.db_manager import save_application
from utils.llm_client import llm_client
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_json(text: str) -> dict:
    """Extract and parse the first JSON object found in an LLM response."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def _clean_bullets(text: str) -> str:
    """Normalise escape sequences and strip preamble/postamble from bullet output."""
    text = text.replace('\\n', '\n').strip()
    lines = text.split('\n')
    bullet_lines = [
        line for line in lines
        if line.strip().startswith(('•', '-', '*', '–')) or re.match(r'^\d+[\.\)]', line.strip())
    ]
    return '\n'.join(bullet_lines) if bullet_lines else text


def _extract_numbered_list(text: str) -> List[str]:
    """Pull out numbered items (1. / 1) ) from an LLM response robustly."""
    lines = text.strip().split('\n')
    items = []
    for line in lines:
        line = line.strip()
        if re.match(r'^\d+[\.\)]\s+', line):
            cleaned = re.sub(r'^\d+[\.\)]\s+', '', line).strip()
            if cleaned:
                items.append(cleaned)
    return items


def _is_valid_skill(skill: str) -> bool:
    """
    Filter out placeholder or generic skill names returned by the LLM.
    Rejects: 'skill1', 'skill2', 'skill 1', 'example', single chars, etc.
    """
    skill_lower = skill.lower().strip()
    if not skill_lower or len(skill_lower) < 2:
        return False
    # Reject obvious placeholders
    placeholder_patterns = [
        r'^skill\s*\d+$',
        r'^example\s*\d*$',
        r'^placeholder',
        r'^n/a$',
        r'^tbd$',
        r'^none$',
        r'^\d+$',
    ]
    for pattern in placeholder_patterns:
        if re.match(pattern, skill_lower):
            return False
    return True


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def parse_resume(resume_path: str) -> Dict[str, Any]:
    """Tool: Parse resume PDF."""
    text = parse_resume_pdf(resume_path)
    return {
        'resume_text': text or 'Parsing failed',
        'success': text is not None
    }


def analyze_job_description(job_desc: str) -> Dict[str, Any]:
    """Tool: Analyze job description for skills, role, and requirements."""
    try:
        response = llm_client.chat(
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a job description analyst. '
                        'Return ONLY valid JSON — no markdown, no code blocks, no extra text.'
                    )
                },
                {
                    'role': 'user',
                    'content': (
                        'Analyze the job description below and return this exact JSON structure:\n'
                        '{\n'
                        '  "job_title": "string",\n'
                        '  "experience_level": "Junior | Mid | Senior",\n'
                        '  "required_skills": ["skill1", "skill2"],\n'
                        '  "key_responsibilities": ["responsibility1", "responsibility2"]\n'
                        '}\n\n'
                        f'Job Description:\n{job_desc[:3000]}'
                    )
                }
            ]
        )

        parsed = _safe_json(response)

        # Extract skills via regex — reliable ground truth
        skills_from_text = extract_skills_from_text(job_desc, 'job_description')

        # Get LLM-extracted skills but filter out placeholders
        llm_skills = [
            s for s in parsed.get('required_skills', [])
            if _is_valid_skill(s)
        ]

        # Merge: regex skills first (more reliable), then any unique LLM skills
        merged_skills = list(dict.fromkeys(skills_from_text + llm_skills))

        return {
            'job_title': parsed.get('job_title', 'Unknown'),
            'experience_level': parsed.get('experience_level', 'Mid'),
            'required_skills': merged_skills,
            'key_responsibilities': parsed.get('key_responsibilities', []),
            'full_analysis': response
        }

    except Exception as e:
        return {'error': str(e)}


def extract_resume_skills(resume_text: str) -> Dict[str, Any]:
    """Tool: Extract skills from resume."""
    skills = extract_skills_from_text(resume_text, 'resume')
    return {'resume_skills': skills}


def skill_gap_analysis(resume_skills: List[str], job_skills: List[str]) -> Dict[str, Any]:
    """Tool: Perform skill gap analysis using FAISS semantic matching."""
    # Filter placeholders from both lists before comparison
    clean_resume = [s for s in resume_skills if _is_valid_skill(s)]
    clean_job    = [s for s in job_skills    if _is_valid_skill(s)]

    table, ats_score = compare_skills(clean_resume, clean_job)
    missing = [row['job_skill'] for row in table if row['status'] == 'Missing']
    return {
        'gap_table':      table,
        'ats_score':      ats_score,
        'missing_skills': missing
    }


def optimize_resume(resume_text: str, job_desc: str, original_bullets: str) -> Dict[str, Any]:
    """Tool: Optimize resume bullet points."""
    try:
        job_keywords = ' | '.join(
            extract_skills_from_text(job_desc, 'job_description')[:15]
        )

        response = llm_client.chat(
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a professional resume writer with 10 years of experience. '
                        'Your task is to rewrite resume bullet points to better match a job description. '
                        'Return ONLY the bullet points — no headers, no explanations, no JSON, no preamble.'
                    )
                },
                {
                    'role': 'user',
                    'content': (
                        f'Rewrite the resume bullets below to match this job.\n\n'
                        f'Key job keywords: {job_keywords}\n\n'
                        f'Original bullets:\n{original_bullets}\n\n'
                        f'Rules:\n'
                        f'- Start every bullet with a strong action verb\n'
                        f'- Weave in job keywords naturally\n'
                        f'- Keep each bullet under 20 words\n'
                        f'- Return 5–7 bullet points only\n'
                        f'- Format: • bullet text\n'
                        f'- Do NOT include any text before or after the bullets'
                    )
                }
            ]
        )

        optimized = _clean_bullets(response)
        return {'optimized_bullets': optimized}

    except Exception as e:
        return {'error': str(e)}


def generate_cover_letter(
    job_title: str,
    job_desc: str,
    resume_summary: str,
    strengths: str,
    missing_skills: List[str]
) -> Dict[str, Any]:
    """Tool: Generate a tailored, professional cover letter."""
    try:
        skills_note = (
            f'Note: Candidate is actively learning: {", ".join(missing_skills[:3])}.'
            if missing_skills else ''
        )

        response = llm_client.chat(
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a professional cover letter writer. '
                        'Write confident, specific, and concise cover letters. '
                        'Return ONLY the letter text — no subject line, no JSON, no markdown formatting.'
                    )
                },
                {
                    'role': 'user',
                    'content': (
                        f'Write a cover letter for this job application.\n\n'
                        f'Job Title: {job_title}\n'
                        f'Job Description Summary: {job_desc[:600]}\n'
                        f'Candidate Summary: {resume_summary}\n'
                        f'Top Strengths: {strengths}\n'
                        f'{skills_note}\n\n'
                        f'Structure:\n'
                        f'Paragraph 1 (2–3 sentences): Why you are excited about this role.\n'
                        f'Paragraph 2 (3–4 sentences): Two specific strengths with examples.\n'
                        f'Paragraph 3 (2 sentences): Call to action and closing.\n\n'
                        f'Tone: Professional but warm.\n'
                        f'Length: 200–250 words maximum.\n'
                        f'Do NOT include placeholders like [Your Name] or [Date].'
                    )
                }
            ]
        )

        cover_letter = response.replace('\\n', '\n').strip()
        return {'cover_letter': cover_letter}

    except Exception as e:
        return {'error': str(e)}


def generate_interview_questions(job_desc: str, resume_skills: List[str]) -> Dict[str, Any]:
    """Tool: Generate categorised interview questions for the role."""
    try:
        skills_str = ', '.join(resume_skills[:10]) if resume_skills else 'Not specified'

        response = llm_client.chat(
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a senior technical interviewer. '
                        'Return ONLY a numbered list of interview questions. '
                        'No preamble, no category headers, no explanations after questions.'
                    )
                },
                {
                    'role': 'user',
                    'content': (
                        f'Generate exactly 10 interview questions for this role.\n\n'
                        f'Job Description:\n{job_desc[:1000]}\n\n'
                        f'Candidate Skills: {skills_str}\n\n'
                        f'Format strictly as:\n'
                        f'1. [question]\n'
                        f'2. [question]\n'
                        f'...\n'
                        f'10. [question]\n\n'
                        f'Mix: 5 technical, 3 behavioral, 2 situational. No headers.'
                    )
                }
            ]
        )

        questions = _extract_numbered_list(response)
        if not questions:
            questions = [
                line.strip() for line in response.strip().split('\n')
                if len(line.strip()) > 20
            ]

        return {'interview_questions': questions[:10]}

    except Exception as e:
        return {'error': str(e)}


def skill_improvement_suggestions(missing_skills: List[str]) -> Dict[str, Any]:
    """Tool: Suggest a personalised learning roadmap for missing skills."""
    # Filter placeholders before passing to LLM
    clean_missing = [s for s in missing_skills if _is_valid_skill(s)]

    if not clean_missing:
        return {'suggestions': []}

    try:
        skills_str = ', '.join(clean_missing[:5])

        response = llm_client.chat(
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a learning and development advisor. '
                        'Return a structured, actionable learning roadmap. '
                        'No preamble or closing remarks.'
                    )
                },
                {
                    'role': 'user',
                    'content': (
                        f'Create a learning roadmap for these missing skills: {skills_str}\n\n'
                        f'For each skill, provide:\n'
                        f'1. Best paid course (Coursera or Udemy — include course name)\n'
                        f'2. Best free resource (official docs or YouTube channel name)\n'
                        f'3. Estimated time to basic proficiency (in weeks)\n\n'
                        f'Format as a numbered list, one skill per entry. '
                        f'Keep each entry to 3 lines maximum.'
                    )
                }
            ]
        )

        suggestions = [
            line.strip()
            for line in response.strip().split('\n')
            if line.strip()
        ]
        return {'suggestions': suggestions}

    except Exception as e:
        fallback = [
            f"{skill}: Search '{skill} for beginners' on Coursera or YouTube"
            for skill in clean_missing
        ]
        return {'suggestions': fallback}