import re
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Dict

# ---------------------------------------------------------------------------
# Model — loaded once at import time, reused for all comparisons
# ---------------------------------------------------------------------------
# 'all-MiniLM-L6-v2' is small (80MB), fast, and accurate enough for skill matching
_model = SentenceTransformer('all-MiniLM-L6-v2')

# Similarity threshold — skills with cosine similarity >= this are considered a match
SIMILARITY_THRESHOLD = 0.75

# ---------------------------------------------------------------------------
# Skill keyword list for regex-based extraction
# ---------------------------------------------------------------------------
SKILL_KEYWORDS = [
    # Languages
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
    'kotlin', 'swift', 'r', 'scala', 'matlab', 'bash', 'shell',
    # Web
    'react', 'angular', 'vue', 'node', 'nodejs', 'express', 'django', 'flask',
    'fastapi', 'html', 'css', 'tailwind', 'bootstrap', 'nextjs', 'graphql', 'rest',
    # Data / ML / AI
    'machine learning', 'deep learning', 'neural networks', 'nlp',
    'natural language processing', 'computer vision', 'reinforcement learning',
    'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn', 'xgboost',
    'huggingface', 'transformers', 'llm', 'generative ai', 'gen-ai', 'rag',
    'pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn', 'plotly',
    # Data engineering
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
    'spark', 'hadoop', 'kafka', 'airflow', 'dbt', 'snowflake', 'bigquery',
    # Cloud / DevOps
    'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'terraform',
    'ci/cd', 'jenkins', 'github actions', 'linux', 'git',
    # Other
    'agile', 'scrum', 'microservices', 'api', 'opencv', 'flask', 'fastapi',
]


def extract_skills_from_text(text: str, source_type: str = 'resume') -> List[str]:
    """
    Extract skills from text using keyword matching.

    Args:
        text:        Raw text from resume or job description.
        source_type: 'resume' or 'job_description' (unused but kept for API compatibility).

    Returns:
        Deduplicated list of skill strings found in the text.
    """
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill.title())
    return list(dict.fromkeys(found))  # deduplicate, preserve order


def compare_skills(
    resume_skills: List[str],
    job_skills: List[str],
) -> Tuple[List[Dict], float]:
    """
    Compare resume skills against job skills using FAISS semantic similarity.

    Each job skill is matched against the closest resume skill using cosine
    similarity on sentence embeddings. Skills with similarity >= SIMILARITY_THRESHOLD
    are marked as matched even if they don't share exact keywords.

    Args:
        resume_skills: Skills extracted from the resume.
        job_skills:    Skills required by the job description.

    Returns:
        Tuple of:
            - gap_table: List of dicts with job_skill, best_match, similarity, status
            - ats_score: Float 0–100 representing percentage of job skills matched
    """
    if not resume_skills or not job_skills:
        table = [
            {'job_skill': s, 'best_match': '', 'similarity': 0.0, 'status': 'Missing'}
            for s in job_skills
        ]
        return table, 0.0

    # --- Embed all skills ---
    # Lowercase for better embedding consistency
    resume_lower = [s.lower() for s in resume_skills]
    job_lower    = [s.lower() for s in job_skills]

    resume_embeddings = _model.encode(resume_lower, normalize_embeddings=True)
    job_embeddings    = _model.encode(job_lower,    normalize_embeddings=True)

    # --- Build FAISS index over resume embeddings ---
    dim = resume_embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product = cosine similarity (embeddings are normalized)
    index.add(resume_embeddings.astype(np.float32))

    # --- Search: for each job skill, find closest resume skill ---
    similarities, indices = index.search(job_embeddings.astype(np.float32), k=1)

    # --- Build gap table ---
    table = []
    matched = 0

    for i, job_skill in enumerate(job_skills):
        sim   = float(similarities[i][0])
        idx   = int(indices[i][0])
        match = resume_skills[idx] if idx < len(resume_skills) else ''

        if sim >= SIMILARITY_THRESHOLD:
            status = 'Match'
            matched += 1
        else:
            status = 'Missing'

        table.append({
            'job_skill':  job_skill,
            'best_match': match,
            'similarity': round(sim, 3),
            'status':     status,
        })

    ats_score = (matched / len(job_skills)) * 100 if job_skills else 0.0
    return table, round(ats_score, 1)