import os
import tempfile
import streamlit as st
from dotenv import load_dotenv

from agent.planner import create_plan, get_plan_summary
from agent.executor import execute_plan
from agent.memory import AgentMemory
from agent.evaluator import evaluate_resume_match
from database.db_manager import get_applications

load_dotenv()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Agentic Job Application Assistant",
    page_icon="🤖",
    layout="wide"
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
# All results are stored in session_state so they survive widget interactions
# and Streamlit reruns without re-running the entire agent pipeline.
if 'results' not in st.session_state:
    st.session_state.results = None
if 'eval_result' not in st.session_state:
    st.session_state.eval_result = None
if 'memory' not in st.session_state:
    st.session_state.memory = None
if 'plan' not in st.session_state:
    st.session_state.plan = None

# ---------------------------------------------------------------------------
# Sidebar — application history
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("📁 Application History")
    try:
        applications = get_applications()
        if applications:
            for app in applications[-5:][::-1]:  # most recent first
                st.markdown(
                    f"**{app.get('job_role', app.get('job_title', 'Unknown'))}**  \n"
                    f"ATS: `{app.get('ats_score', 0)}%`"
                )
                st.divider()
        else:
            st.caption("No previous analyses yet.")
    except Exception as e:
        st.caption(f"History unavailable: {e}")

    st.header("ℹ️ How it works")
    for line in get_plan_summary():
        st.caption(line)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🤖 Agentic Job Application Assistant")
st.markdown(
    "Upload your resume and paste a job description. "
    "The AI agent will analyse, optimise, and prepare you — automatically."
)

# ---------------------------------------------------------------------------
# Input area
# ---------------------------------------------------------------------------
col1, col2 = st.columns([1, 1])

with col1:
    resume_file = st.file_uploader("📄 Upload Resume (PDF)", type="pdf")

with col2:
    job_desc = st.text_area(
        "📋 Job Description",
        height=200,
        placeholder="Paste the full job description here..."
    )

run_button = st.button("🚀 Analyse Job Application", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Agent execution
# ---------------------------------------------------------------------------
if run_button:
    if not resume_file:
        st.error("Please upload your resume (PDF).")
        st.stop()
    if not job_desc.strip():
        st.error("Please paste the job description.")
        st.stop()

    # Save uploaded PDF to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(resume_file.getvalue())
        resume_path = tmp.name

    memory = AgentMemory()
    plan = create_plan(resume_path, job_desc)

    # --- Live step-by-step progress ---
    st.markdown("### ⚡ Agent running...")
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    step_log = st.empty()

    total_steps = len(plan)

    # Monkey-patch memory.add_step to update UI progress live
    original_add_step = memory.add_step

    def _tracked_add_step(step_name, input_data, output_data):
        original_add_step(step_name, input_data, output_data)
        completed = len(memory.conversation_history)
        progress_bar.progress(completed / total_steps)
        status_text.markdown(f"**Step {completed}/{total_steps}** — `{step_name}` ✓")
        summary = memory.get_session_summary()
        if summary['failed_steps']:
            step_log.warning(f"Failed steps so far: {', '.join(summary['failed_steps'])}")

    memory.add_step = _tracked_add_step

    status_text.markdown("**Step 0/{total_steps}** — starting…")

    results = execute_plan(plan, resume_path, job_desc, memory)

    # Evaluate using already-computed gap_analysis (no duplicate calculation)
    eval_result = evaluate_resume_match(
        resume_skills=results.get('resume_skills', []),
        job_skills=results.get('job_skills', []),
        ats_score=results.get('ats_score', 0),
        gap_analysis=results.get('gap_analysis'),   # ← key fix: reuse existing data
    )

    # Persist to DB via memory (handles errors internally)
    memory.save_to_db(
        resume_path=resume_path,
        job_title=results.get('jd_analysis', {}).get('job_title', 'Unknown'),
        ats_score=results.get('ats_score', 0),
    )

    # Store in session_state so results survive tab clicks and reruns
    st.session_state.results = results
    st.session_state.eval_result = eval_result
    st.session_state.memory = memory
    st.session_state.plan = plan

    progress_bar.progress(1.0)
    status_text.markdown(f"✅ **Analysis complete** — {total_steps} steps finished.")

    # Cleanup temp file
    try:
        os.unlink(resume_path)
    except Exception:
        pass

    # Show any failed steps as warnings
    failed = memory.get_failed_steps()
    if failed:
        st.warning(f"⚠️ Some steps had errors and were skipped: {', '.join(failed)}")

# ---------------------------------------------------------------------------
# Results display — rendered OUTSIDE the run block so they persist on rerun
# ---------------------------------------------------------------------------
if st.session_state.results:
    results = st.session_state.results
    eval_result = st.session_state.eval_result
    memory = st.session_state.memory

    st.markdown("---")
    st.markdown("### 📊 Results")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Skill Gap",
        "🎯 ATS Score",
        "✏️ Resume",
        "📝 Cover Letter",
        "❓ Interview Prep",
        "🎓 Skill Roadmap",
        "📈 Summary",
    ])

    # --- Tab 1: Skill Gap Analysis ---
    with tab1:
        st.subheader("Skill Gap Analysis")
        gap = results.get('gap_analysis', {})
        if gap.get('gap_table'):
            st.dataframe(gap['gap_table'], use_container_width=True)
            missing = gap.get('missing_skills', [])
            if missing:
                st.markdown("**Missing skills:**")
                cols = st.columns(min(len(missing), 4))
                for i, skill in enumerate(missing):
                    cols[i % 4].error(skill)
        else:
            st.warning("Skill gap analysis did not complete.")

    # --- Tab 2: ATS Score ---
    with tab2:
        st.subheader("ATS Compatibility Score")
        score = results.get('ats_score', 0)
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("ATS Score", f"{score:.1f}%")
        col_b.metric("Match Level", eval_result.get('match_level', 'N/A'))
        col_c.metric(
            "Skills Matched",
            f"{eval_result.get('strengths_count', 0)} / "
            f"{eval_result.get('strengths_count', 0) + eval_result.get('skill_gaps_count', 0)}"
        )
        st.progress(min(score / 100, 1.0))

        col_d, col_e = st.columns(2)
        with col_d:
            st.markdown("**Matched skills**")
            for s in eval_result.get('strengths', []):
                st.success(s)
        with col_e:
            st.markdown("**Missing skills**")
            for s in eval_result.get('gaps', []):
                st.error(s)

    # --- Tab 3: Resume Optimisation ---
    with tab3:
        st.subheader("Optimised Resume Bullets")
        optimized = results.get('optimized_resume', '')
        if optimized:
            st.markdown(optimized)
            st.download_button(
                "⬇️ Download optimised bullets",
                data=optimized,
                file_name="optimized_resume_bullets.txt",
                mime="text/plain",
            )
        else:
            st.warning("Resume optimisation did not complete.")

    # --- Tab 4: Cover Letter ---
    with tab4:
        st.subheader("AI-Generated Cover Letter")
        cover = results.get('cover_letter', '')
        if cover:
            st.markdown(cover)
            st.download_button(
                "⬇️ Download cover letter",
                data=cover,
                file_name="cover_letter.txt",
                mime="text/plain",
            )
        else:
            st.warning("Cover letter generation did not complete.")

    # --- Tab 5: Interview Questions ---
    with tab5:
        st.subheader("Targeted Interview Questions")
        questions = results.get('interview_questions', [])
        if questions:
            for i, q in enumerate(questions, 1):
                with st.expander(f"Question {i}"):
                    st.write(q)
        else:
            st.warning("Interview questions did not generate.")

    # --- Tab 6: Skill Roadmap ---
    with tab6:
        st.subheader("Personalised Learning Roadmap")
        suggestions = results.get('skill_suggestions', [])
        if suggestions:
            for sug in suggestions:
                if sug.strip():
                    st.markdown(f"🎓 {sug}")
        else:
            st.warning("Skill suggestions did not generate.")

    # --- Tab 7: Summary ---
    with tab7:
        st.subheader("Analysis Summary")

        rec = eval_result.get('recommendation', '')
        score = eval_result.get('ats_score', 0)
        if score > 70:
            st.success(f"✅ {rec}")
        elif score > 50:
            st.warning(f"⚠️ {rec}")
        else:
            st.error(f"❌ {rec}")

        st.markdown(eval_result.get('summary', ''))

        col_f, col_g, col_h = st.columns(3)
        col_f.metric("Resume Skills Found", len(results.get('resume_skills', [])))
        col_g.metric("Job Skills Required", len(results.get('job_skills', [])))
        col_h.metric("Steps Completed", memory.get_session_summary()['completed_steps'])

        with st.expander("🔍 View agent plan & execution log"):
            st.markdown("**Plan**")
            st.json(st.session_state.plan)
            st.markdown("**Execution context**")
            st.text(memory.get_context(max_steps=8))

        with st.expander("🔍 View all extracted skills"):
            col_i, col_j = st.columns(2)
            with col_i:
                st.markdown("**Resume skills**")
                st.write(results.get('resume_skills', []))
            with col_j:
                st.markdown("**Job required skills**")
                st.write(results.get('job_skills', []))

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption("Powered by Ollama (local LLM) · Agentic architecture · Streamlit UI")