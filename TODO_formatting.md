# Fix UI Formatting Issues

Status: Planning

1. Edit app.py: st.text_area → st.markdown for Resume Optimization & Cover Letter tabs
2. Edit agent/tools.py: 
   - Add 'Respond as markdown bullets/cover letter. No JSON.' to prompts
   - Post-process interview_questions/skill_suggestions: replace \\n → \n, strip
3. Edit agent/planner.py: Robust JSON parse
4. Test app outputs are formatted (bullets, letters, lists)
5. attempt_completion
