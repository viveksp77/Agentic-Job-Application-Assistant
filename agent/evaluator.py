import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def evaluate_resume_match(
    resume_skills: List[str],
    job_skills: List[str],
    ats_score: float,
    gap_analysis: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Evaluate the resume-job match using results already computed by skill_gap_analysis.

    Reuses `gap_analysis` from the executor context instead of calling compare_skills()
    again — avoids duplicate computation and ensures the UI summary tab always
    shows the same score as the ATS tab.

    Args:
        resume_skills: Skills extracted from the resume.
        job_skills:    Skills required by the job description.
        ats_score:     Score already computed by skill_gap_analysis (0–100).
        gap_analysis:  Full output of skill_gap_analysis (optional but preferred).

    Returns:
        Evaluation dict consumed by the Summary tab.
    """
    if not job_skills:
        logger.warning("evaluate_resume_match called with no job skills")
        return {
            'match_level': 'Unknown',
            'is_good_match': False,
            'ats_score': 0,
            'recommendation': 'No job skills detected — please check the job description.',
            'strengths': [],
            'gaps': [],
            'strengths_count': 0,
            'skill_gaps_count': 0,
            'summary': 'Unable to evaluate — no job skills found.',
        }

    # Prefer pre-computed gap table; fall back to recomputing only if missing
    if gap_analysis and 'gap_table' in gap_analysis:
        table = gap_analysis['gap_table']
        score = ats_score  # trust the already-computed score
        logger.debug("Evaluator reusing existing gap_analysis (score=%.1f)", score)
    else:
        logger.warning("gap_analysis not provided — recomputing (score may differ from ATS tab)")
        from utils.skill_extractor import compare_skills
        table, score = compare_skills(resume_skills, job_skills)

    strengths = [row['job_skill'] for row in table if row['status'] == 'Match']
    gaps = [row['job_skill'] for row in table if row['status'] == 'Missing']

    # Match level thresholds
    if score > 85:
        match_level = 'Excellent'
        recommendation = 'Apply immediately — excellent match!'
    elif score > 70:
        match_level = 'Good'
        recommendation = 'Strong candidate — apply with confidence!'
    elif score > 50:
        match_level = 'Fair'
        recommendation = 'Good potential — optimise your resume before applying.'
    else:
        match_level = 'Poor'
        recommendation = 'Major gaps detected — consider upskilling before applying.'

    evaluation = {
        'is_good_match': score > 70,
        'match_level': match_level,
        'ats_score': round(score, 1),
        'strengths_count': len(strengths),
        'skill_gaps_count': len(gaps),
        'strengths': strengths[:6],
        'gaps': gaps[:6],
        'recommendation': recommendation,
        'summary': (
            f"ATS Score: {score:.1f}% | "
            f"Matched: {len(strengths)} skills | "
            f"Missing: {len(gaps)} skills"
        ),
    }

    logger.info(
        "Evaluation complete — %s (%.1f%%) | %d strengths | %d gaps",
        match_level, score, len(strengths), len(gaps),
    )
    return evaluation