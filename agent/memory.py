import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Max characters stored per output in memory — prevents unbounded RAM usage
# when resume text or cover letters are stored as step outputs.
_MAX_OUTPUT_CHARS = 500


class AgentMemory:
    def __init__(self):
        self.conversation_history: List[Dict[str, Any]] = []
        self.results: Dict[str, Any] = {}
        self.db_history: List[Dict[str, Any]] = []
        self.session_start: str = datetime.now().isoformat()
        self.load_from_db()

    # ------------------------------------------------------------------
    # DB integration
    # ------------------------------------------------------------------

    def load_from_db(self) -> None:
        """Load the 3 most recent analyses from the database into context."""
        try:
            from database.db_manager import get_applications
            apps = get_applications()
            self.db_history = apps[-3:] if apps else []
            logger.debug("Loaded %d past applications from DB", len(self.db_history))
        except Exception as e:
            # DB unavailable (first run, missing file, etc.) — not a fatal error
            logger.warning("Could not load DB history: %s", e)
            self.db_history = []

    def save_to_db(self, resume_path: str = '', job_title: str = '', ats_score: float = 0.0) -> None:
        """
        Persist a summary of the current session to the database.

        Args:
            resume_path: Path to the uploaded resume PDF.
            job_title:   Job title extracted during analysis.
            ats_score:   Final ATS compatibility score (0–100).
        """
        try:
            from database.db_manager import save_application
            save_application(
                resume_path=resume_path,
                job_title=job_title,
                ats_score=ats_score,
                steps_run=[s['step'] for s in self.conversation_history],
                timestamp=self.session_start,
            )
            logger.info("Session saved to DB (job_title=%s, ats=%.1f)", job_title, ats_score)
        except Exception as e:
            logger.warning("Could not save session to DB: %s", e)

    # ------------------------------------------------------------------
    # Step tracking
    # ------------------------------------------------------------------

    def add_step(self, step_name: str, input_data: Dict, output_data: Dict) -> None:
        """
        Record a completed tool step.

        Large values (resume text, cover letters) are truncated in memory
        to avoid unbounded growth across long sessions. The full data lives
        in the executor's `results` dict — memory is for context and logging.

        Args:
            step_name:   Name of the tool that ran (e.g. 'parse_resume').
            input_data:  Arguments passed to the tool.
            output_data: Dict returned by the tool.
        """
        # Sanitize output — truncate large string values before storing
        sanitized_output = {
            k: (v[:_MAX_OUTPUT_CHARS] + '…' if isinstance(v, str) and len(v) > _MAX_OUTPUT_CHARS else v)
            for k, v in output_data.items()
        }

        self.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'step': step_name,
            'input': input_data,
            'output': sanitized_output,
            'status': 'error' if output_data.get('error') else 'success',
        })

        # Store latest result per tool (overwrite if the tool ran twice)
        self.results[step_name] = sanitized_output

    def get_step(self, step_name: str) -> Optional[Dict[str, Any]]:
        """Return the most recent output for a given tool, or None."""
        return self.results.get(step_name)

    def get_failed_steps(self) -> List[str]:
        """Return names of all steps that completed with an error."""
        return [
            s['step'] for s in self.conversation_history
            if s.get('status') == 'error'
        ]

    # ------------------------------------------------------------------
    # Context for LLM / UI
    # ------------------------------------------------------------------

    def get_context(self, max_steps: int = 5) -> str:
        """
        Build a compact context string for LLM prompts or UI display.

        Shows only the most recent `max_steps` steps and whether each
        succeeded or failed — not raw output, which can be very large.

        Args:
            max_steps: How many recent steps to include.

        Returns:
            Multi-line string summary of recent agent activity.
        """
        recent = self.conversation_history[-max_steps:]

        if not recent:
            return 'No steps completed yet.'

        lines = []
        for r in recent:
            status_icon = '✓' if r.get('status') == 'success' else '✗'
            # Show first 120 chars of the first string value in the output
            preview = next(
                (str(v)[:120] for v in r['output'].values() if isinstance(v, str) and v),
                'no text output'
            )
            lines.append(f"{status_icon} {r['step']} — {preview}")

        if self.db_history:
            lines.append(f"\n{len(self.db_history)} previous analyses available in history.")

        return '\n'.join(lines)

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Return a structured summary of the current session.
        Useful for the Summary tab and for save_to_db().
        """
        total = len(self.conversation_history)
        failed = self.get_failed_steps()
        return {
            'session_start': self.session_start,
            'total_steps': total,
            'completed_steps': total - len(failed),
            'failed_steps': failed,
            'tools_run': [s['step'] for s in self.conversation_history],
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Reset in-memory state for a new analysis session."""
        self.conversation_history = []
        self.results = {}
        self.session_start = datetime.now().isoformat()
        logger.debug("AgentMemory cleared for new session")