import json
import re
from typing import Dict, Any, List

from utils.pdf_parser import parse_resume_pdf
from utils.skill_extractor import extract_skills_from_text, compare_skills
from utils.rag_memory import store_resume, query_resume
from database.db_manager import save_application
from utils.llm_client import llm_client
import os
from dotenv import load_dotenv

load_dotenv()

def _safe_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}

def _clean_bullets(text):
    text = text.replace('\\n', '\n').strip()
    lines = text.split('\n')
    bullet_lines = [l for l in lines if l.strip().startswith(('•','-','*','–')) or re.match(r'^\d+[\.\)]', l.strip())]
    return '\n'.join(bullet_lines) if bullet_lines else text

def _extract_numbered_list(text):
    items = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if re.match(r'^\d+[\.\)]\s+', line):
            cleaned = re.sub(r'^\d+[\.\)]\s+', '', line).strip()
            if cleaned:
                items.append(cleaned)
    return items

def _is_valid_skill(skill):
    s = skill.lower().strip()
    if not s or len(s) < 2:
        return False
    for p in [r'^skill\s*\d+$', r'^example\s*\d*$', r'^placeholder', r'^n/a$', r'^tbd$', r'^none$', r'^\d+$']:
        if re.match(p, s):
            return False
    return True

def parse_resume(resume_path):
    text = parse_resume_pdf(resume_path)
    if not text:
        return {'resume_text': 'Parsing failed', 'success': False, 'resume_id': None}
    resume_id = store_resume(text)
    return {'resume_text': text, 'resume_id': resume_id, 'success': True}

def analyze_job_description(job_desc):
    try:
        response = llm_client.chat(messages=[
            {'role': 'system', 'content': 'You are a job description analyst. Return ONLY valid JSON — no markdown, no code blocks, no extra text.'},
            {'role': 'user', 'content': f'Analyze the job description below and return this exact JSON:\n{{"job_title":"string","experience_level":"Junior|Mid|Senior","required_skills":["skill1"],"key_responsibilities":["r1"]}}\n\nJob Description:\n{job_desc[:3000]}'}
        ])
        parsed = _safe_json(response)
        skills_from_text = extract_skills_from_text(job_desc, 'job_description')
        llm_skills = [s for s in parsed.get('required_skills', []) if _is_valid_skill(s)]
        merged = list(dict.fromkeys(skills_from_text + llm_skills))
        return {'job_title': parsed.get('job_title','Unknown'), 'experience_level': parsed.get('experience_level','Mid'), 'required_skills': merged, 'key_responsibilities': parsed.get('key_responsibilities',[]), 'full_analysis': response}
    except Exception as e:
        return {'error': str(e)}

def extract_resume_skills(resume_text, resume_id=None):
    if resume_id:
        ctx = query_resume(resume_id, "technical skills programming languages tools frameworks", n_results=3)
        if ctx:
            skills = extract_skills_from_text(ctx, 'resume')
            if skills:
                return {'resume_skills': skills}
    return {'resume_skills': extract_skills_from_text(resume_text, 'resume')}

def skill_gap_analysis(resume_skills, job_skills):
    clean_r = [s for s in resume_skills if _is_valid_skill(s)]
    clean_j = [s for s in job_skills if _is_valid_skill(s)]
    table, ats_score = compare_skills(clean_r, clean_j)
    missing = [r['job_skill'] for r in table if r['status'] == 'Missing']
    return {'gap_table': table, 'ats_score': ats_score, 'missing_skills': missing}

def optimize_resume(resume_text, job_desc, original_bullets, resume_id=None):
    try:
        job_keywords = ' | '.join(extract_skills_from_text(job_desc, 'job_description')[:15])
        if resume_id:
            ctx = query_resume(resume_id, "work experience projects achievements", n_results=3)
            bullets_to_use = ctx if ctx else original_bullets
        else:
            bullets_to_use = original_bullets
        response = llm_client.chat(messages=[
            {'role': 'system', 'content': 'You are a professional resume writer. Return ONLY bullet points — no headers, no explanations, no JSON.'},
            {'role': 'user', 'content': f'Rewrite resume bullets to match this job.\n\nJob keywords: {job_keywords}\n\nResume experience:\n{bullets_to_use[:1500]}\n\nRules:\n- Start with action verb\n- Weave in keywords\n- Under 20 words each\n- 5-7 bullets\n- Format: • bullet\n- Nothing before or after bullets'}
        ])
        return {'optimized_bullets': _clean_bullets(response)}
    except Exception as e:
        return {'error': str(e)}

def generate_cover_letter(job_title, job_desc, resume_summary, strengths, missing_skills, resume_id=None):
    try:
        skills_note = f'Candidate is actively learning: {", ".join(missing_skills[:3])}.' if missing_skills else ''
        if resume_id:
            exp = query_resume(resume_id, "work experience internship responsibilities", n_results=2)
            ach = query_resume(resume_id, "achievements awards projects impact results", n_results=2)
            candidate_context = f"{exp}\n\n{ach}".strip()
        else:
            candidate_context = resume_summary
        response = llm_client.chat(messages=[
            {'role': 'system', 'content': 'You are a professional cover letter writer. Return ONLY the letter text — no subject line, no JSON, no markdown.'},
            {'role': 'user', 'content': f'Write a cover letter.\n\nJob Title: {job_title}\nJob Description: {job_desc[:600]}\nCandidate Background:\n{candidate_context[:800]}\nStrengths: {strengths}\n{skills_note}\n\nStructure:\nP1 (2-3 sentences): Excitement for role.\nP2 (3-4 sentences): Two strengths with examples.\nP3 (2 sentences): Call to action.\n\nMax 250 words. No placeholders.'}
        ])
        return {'cover_letter': response.replace('\\n', '\n').strip()}
    except Exception as e:
        return {'error': str(e)}

def generate_interview_questions(job_desc, resume_skills, resume_id=None):
    try:
        skills_str = ', '.join(resume_skills[:10]) if resume_skills else 'Not specified'
        bg = query_resume(resume_id, "projects experience skills education", n_results=3) if resume_id else ''
        response = llm_client.chat(messages=[
            {'role': 'system', 'content': 'You are a senior technical interviewer. Return ONLY a numbered list. No preamble, no headers.'},
            {'role': 'user', 'content': f'Generate exactly 10 interview questions.\n\nJob: {job_desc[:800]}\nSkills: {skills_str}\nBackground:\n{bg[:600]}\n\nFormat:\n1. [question]\n...\n10. [question]\n\nMix: 5 technical, 3 behavioral, 2 situational. Personalise where possible.'}
        ])
        questions = _extract_numbered_list(response)
        if not questions:
            questions = [l.strip() for l in response.strip().split('\n') if len(l.strip()) > 20]
        return {'interview_questions': questions[:10]}
    except Exception as e:
        return {'error': str(e)}

def skill_improvement_suggestions(missing_skills):
    clean = [s for s in missing_skills if _is_valid_skill(s)]
    if not clean:
        return {'suggestions': []}
    try:
        response = llm_client.chat(messages=[
            {'role': 'system', 'content': 'You are a learning advisor. Return a structured roadmap. No preamble.'},
            {'role': 'user', 'content': f'Learning roadmap for: {", ".join(clean[:5])}\n\nFor each skill:\n1. Best paid course (Coursera/Udemy)\n2. Best free resource\n3. Time estimate (weeks)\n\nNumbered list, 3 lines per skill max.'}
        ])
        return {'suggestions': [l.strip() for l in response.strip().split('\n') if l.strip()]}
    except Exception as e:
        return {'suggestions': [f"{s}: Search on Coursera or YouTube" for s in clean]}