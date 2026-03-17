import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

from agent.tools import (
    parse_resume,
    analyze_job_description,
    extract_resume_skills,
    skill_gap_analysis,
    optimize_resume,
    generate_cover_letter,
    generate_interview_questions,
    skill_improvement_suggestions,
)
from agent.memory import AgentMemory

logger = logging.getLogger(__name__)


def _extract_bullets_from_resume(resume_text: str) -> str:
    lines = resume_text.split('\n')
    bullets = [
        line.strip() for line in lines
        if re.match(r'^[\•\-\*\–]', line.strip()) or re.match(r'^\d+[\.\)]', line.strip())
    ]
    return '\n'.join(bullets[:20]) if bullets else resume_text[500:2000].strip()


def _run(fn, *args, **kwargs):
    """Run a tool and return (tool_name, result)."""
    name = fn.__name__
    try:
        result = fn(*args, **kwargs)
        if result.get('error'):
            raise RuntimeError(result['error'])
        logger.info("  ✓ %s", name)
        return name, result
    except Exception as e:
        logger.warning("  ✗ %s failed: %s", name, e)
        return name, {'error': str(e)}


def execute_plan(
    plan: List[Dict],
    resume_path: str,
    job_desc: str,
    memory: AgentMemory = None,
) -> Dict[str, Any]:
    """
    Multi-agent parallel executor — 3 phases.

    Phase 1 (parallel): parse_resume + analyze_job_description
    Phase 2 (sequential): extract_resume_skills → skill_gap_analysis
    Phase 3 (parallel): optimize_resume + cover_letter + interview_questions + suggestions
    """
    if memory is None:
        memory = AgentMemory()

    results: Dict[str, Any] = {
        'resume_text':         '',
        'resume_id':           None,
        'jd_analysis':         {},
        'resume_skills':       [],
        'job_skills':          [],
        'gap_analysis':        {},
        'ats_score':           0,
        'missing_skills':      [],
        'optimized_resume':    '',
        'cover_letter':        '',
        'interview_questions': [],
        'skill_suggestions':   [],
        'steps':               [],
    }

    # ------------------------------------------------------------------
    # Phase 1 — parse resume + analyse JD simultaneously
    # ------------------------------------------------------------------
    # Phase 1 — slight stagger to avoid simultaneous Ollama memory spike
    logger.info("Phase 1 starting")
    import time

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_run, parse_resume, resume_path)
        time.sleep(1)  # let parse_resume start before JD analysis
        f2 = pool.submit(_run, analyze_job_description, job_desc)

    for future in as_completed([f1, f2]):
        name, result = future.result()
        _merge(name, result, results)
        _record(name, result, results, memory)

    # ------------------------------------------------------------------
    # Phase 2 — extract skills, then gap analysis (order matters)
    # ------------------------------------------------------------------
    logger.info("Phase 2 starting")
    name, result = _run(extract_resume_skills, results['resume_text'], results['resume_id'])
    _merge(name, result, results)
    _record(name, result, results, memory)

    name, result = _run(skill_gap_analysis, results['resume_skills'], results['job_skills'])
    _merge(name, result, results)
    _record(name, result, results, memory)
    logger.info("Phase 2 complete")

    # ------------------------------------------------------------------
    # Phase 3 — all generation tools simultaneously
    # ------------------------------------------------------------------
    logger.info("Phase 3 starting (parallel)")
    original_bullets = _extract_bullets_from_resume(results['resume_text'])
    jd = results['jd_analysis']

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(
                _run, optimize_resume,
                results['resume_text'], job_desc, original_bullets, results['resume_id'],
            ): 'optimize_resume',

            pool.submit(
                _run, generate_cover_letter,
                jd.get('job_title', 'the role'),
                job_desc,
                results['resume_text'][:800],
                ', '.join(results['resume_skills'][:6]),
                results['missing_skills'],
                results['resume_id'],
            ): 'generate_cover_letter',

            pool.submit(
                _run, generate_interview_questions,
                job_desc, results['resume_skills'], results['resume_id'],
            ): 'generate_interview_questions',

            pool.submit(
                _run, skill_improvement_suggestions,
                results['missing_skills'],
            ): 'skill_improvement_suggestions',
        }

        for future in as_completed(futures):
            name, result = future.result()
            _merge(name, result, results)
            _record(name, result, results, memory)

    logger.info("Phase 3 complete — all done")
    return results


def _merge(tool_name: str, result: Dict, results: Dict) -> None:
    if tool_name == 'parse_resume':
        results['resume_text'] = result.get('resume_text', '')
        results['resume_id']   = result.get('resume_id')
    elif tool_name == 'analyze_job_description':
        results['jd_analysis'] = result
        results['job_skills']  = result.get('required_skills', [])
    elif tool_name == 'extract_resume_skills':
        results['resume_skills'] = result.get('resume_skills', [])
    elif tool_name == 'skill_gap_analysis':
        results['gap_analysis']   = result
        results['ats_score']      = result.get('ats_score', 0)
        results['missing_skills'] = result.get('missing_skills', [])
    elif tool_name == 'optimize_resume':
        results['optimized_resume'] = result.get('optimized_bullets', '')
    elif tool_name == 'generate_cover_letter':
        results['cover_letter'] = result.get('cover_letter', '')
    elif tool_name == 'generate_interview_questions':
        results['interview_questions'] = result.get('interview_questions', [])
    elif tool_name == 'skill_improvement_suggestions':
        results['skill_suggestions'] = result.get('suggestions', [])


def _record(tool_name: str, result: Dict, results: Dict, memory: AgentMemory) -> None:
    status = 'error' if result.get('error') else 'done'
    results['steps'].append({'tool': tool_name, 'status': status, 'error': result.get('error')})
    memory.add_step(tool_name, {}, result)