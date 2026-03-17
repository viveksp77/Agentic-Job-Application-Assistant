import re
import hashlib
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ChromaDB client — persistent local storage in .chroma/ folder
# ---------------------------------------------------------------------------
_client = chromadb.PersistentClient(path=".chroma")

# Use the same sentence-transformers model already installed for FAISS
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Collection name for resume chunks
COLLECTION_NAME = "resume_chunks"


# ---------------------------------------------------------------------------
# Resume chunking
# ---------------------------------------------------------------------------

def _chunk_resume(resume_text: str) -> List[Dict[str, str]]:
    """
    Split resume text into semantic sections.
    Each chunk has: text, section label, chunk_id.
    """
    # Section headers to detect
    section_patterns = {
        'education':    r'(education|academic|qualification|degree|university|college)',
        'experience':   r'(experience|employment|work history|career|job|internship)',
        'skills':       r'(skill|technical|technology|tools|proficiency|competenc)',
        'projects':     r'(project|portfolio|built|developed|created)',
        'achievements': r'(achievement|award|certification|accomplishment|honor)',
        'summary':      r'(summary|objective|profile|about|overview)',
    }

    lines = resume_text.split('\n')
    chunks = []
    current_section = 'general'
    current_lines = []

    for line in lines:
        line_lower = line.lower().strip()

        # Detect section header
        detected = None
        for section, pattern in section_patterns.items():
            if re.search(pattern, line_lower) and len(line.strip()) < 60:
                detected = section
                break

        if detected:
            # Save current chunk
            if current_lines:
                text = '\n'.join(current_lines).strip()
                if len(text) > 30:
                    chunks.append({'section': current_section, 'text': text})
            current_section = detected
            current_lines = [line]
        else:
            current_lines.append(line)

    # Save last chunk
    if current_lines:
        text = '\n'.join(current_lines).strip()
        if len(text) > 30:
            chunks.append({'section': current_section, 'text': text})

    # If no sections detected, chunk by fixed size
    if len(chunks) <= 1:
        words = resume_text.split()
        chunk_size = 150
        for i in range(0, len(words), chunk_size):
            chunk_text = ' '.join(words[i:i + chunk_size])
            chunks.append({'section': f'chunk_{i // chunk_size}', 'text': chunk_text})

    return chunks


def _resume_id(resume_text: str) -> str:
    """Generate a stable ID for a resume based on its content hash."""
    return hashlib.md5(resume_text[:500].encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def store_resume(resume_text: str) -> str:
    """
    Chunk the resume and store embeddings in ChromaDB.

    Returns the resume_id — pass this to query_resume() later.
    """
    resume_id = _resume_id(resume_text)
    collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_ef,
    )

    chunks = _chunk_resume(resume_text)
    if not chunks:
        logger.warning("No chunks extracted from resume")
        return resume_id

    # Build lists for ChromaDB batch insert
    ids       = [f"{resume_id}_{i}" for i in range(len(chunks))]
    documents = [c['text'] for c in chunks]
    metadatas = [{'section': c['section'], 'resume_id': resume_id} for c in chunks]

    # Delete old chunks for this resume if they exist
    try:
        existing = collection.get(where={"resume_id": resume_id})
        if existing['ids']:
            collection.delete(ids=existing['ids'])
    except Exception:
        pass

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    logger.info("Stored %d chunks for resume %s", len(chunks), resume_id)
    return resume_id


def query_resume(resume_id: str, query: str, n_results: int = 3) -> str:
    """
    Retrieve the most relevant resume chunks for a given query.

    Args:
        resume_id:  ID returned by store_resume().
        query:      What you're looking for (e.g. "technical skills", "work experience").
        n_results:  Number of chunks to retrieve (default 3).

    Returns:
        Concatenated relevant resume text.
    """
    try:
        collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_ef,
        )

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, 10),
            where={"resume_id": resume_id},
        )

        chunks = results.get('documents', [[]])[0]
        if not chunks:
            logger.warning("No chunks found for resume_id=%s", resume_id)
            return ""

        return '\n\n'.join(chunks)

    except Exception as e:
        logger.error("RAG query failed: %s", e)
        return ""


def get_resume_sections(resume_id: str) -> Dict[str, str]:
    """
    Retrieve all stored sections for a resume as a dict.
    Useful for debugging or displaying what was stored.
    """
    try:
        collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_ef,
        )
        results = collection.get(where={"resume_id": resume_id})
        sections = {}
        for doc, meta in zip(results['documents'], results['metadatas']):
            section = meta.get('section', 'general')
            sections[section] = sections.get(section, '') + '\n' + doc
        return sections
    except Exception as e:
        logger.error("get_resume_sections failed: %s", e)
        return {}