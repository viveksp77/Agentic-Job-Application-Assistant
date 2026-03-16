from typing import List, Dict, Any
import importlib
from agent.tools import (
    parse_resume, analyze_job_description, extract_resume_skills,
    skill_gap_analysis, optimize_resume, generate_cover_letter,
    generate_interview_questions, skill_improvement_suggestions
)
from agent.memory import AgentMemory

def execute_plan(plan: List[Dict], resume_path: str, job_desc: str, memory: AgentMemory = None) -> Dict[str, Any]:
    """
    Agent Executor: Sequentially execute planned tools, passing context between steps.
    
    Args:
        plan: List[{'tool_name': str, 'args': dict}]
        resume_path: PDF file path  
        job_desc: Job description text
        memory: AgentMemory instance
        
    Returns:
        Complete results dict for UI
    """
    if memory is None:
        memory = AgentMemory()
    
    results = {
        'resume_text': '',
        'jd_analysis': {},
        'resume_skills': [],
        'job_skills': [],
        'gap_analysis': {},
        'ats_score': 0,
        'optimized_resume': '',
        'cover_letter': '',
        'interview_questions': [],
        'skill_suggestions': ''
    }
    
    for i, step in enumerate(plan, 1):
        tool_name = step['tool_name']
        args = step.get('args', {})
        
        # Inject previous results as context
        args.update({
            'resume_text': results['resume_text'],
            'jd_analysis': results['jd_analysis'], 
            'resume_skills': results['resume_skills'],
            'job_skills': results['job_skills'],
            'gap_analysis': results['gap_analysis']
        })
        
        try:
            # Dynamic tool dispatch
            if tool_name == 'parse_resume':
                result = parse_resume(resume_path)
            elif tool_name == 'analyze_job_description':
                result = analyze_job_description(job_desc)
            elif tool_name == 'extract_resume_skills':
                result = extract_resume_skills(results['resume_text'])
            elif tool_name == 'skill_gap_analysis':
                result = skill_gap_analysis(results['resume_skills'], results['job_skills'])
            elif tool_name == 'optimize_resume':
                result = optimize_resume(results['resume_text'], job_desc, 'Original bullets')
            elif tool_name == 'generate_cover_letter':
                result = generate_cover_letter(
                    results['jd_analysis'].get('job_title', 'Role'),
                    job_desc,
                    results['resume_text'][:1000],
                    str(results['resume_skills'][:5]),
                    str(results['gap_analysis'].get('missing_skills', []))
                )
            elif tool_name == 'generate_interview_questions':
                result = generate_interview_questions(job_desc, results['resume_skills'])
            elif tool_name == 'skill_improvement_suggestions':
                result = skill_improvement_suggestions(results['gap_analysis'].get('missing_skills', []))
            else:
                result = {'error': f'Unknown tool: {tool_name}'}
            
            memory.add_step(tool_name, args, result)
            
            # Update results mapping
            if 'resume_text' in result:
                results['resume_text'] = result['resume_text']
            if 'required_skills' in result:
                results['job_skills'] = result['required_skills']
            if 'resume_skills' in result:
                results['resume_skills'] = result['resume_skills'] 
            if 'gap_table' in result:
                results['gap_analysis'] = result
                results['ats_score'] = result.get('ats_score', 0)
            if 'optimized_bullets' in result:
                results['optimized_resume'] = result['optimized_bullets']
            if 'cover_letter' in result:
                results['cover_letter'] = result['cover_letter']
            if 'interview_questions' in result:
                results['interview_questions'] = result['interview_questions']
            if 'suggestions' in result:
                results['skill_suggestions'] = result['suggestions']
                
        except Exception as e:
            error_result = {'error': f'{tool_name}: {str(e)}'}
            memory.add_step(tool_name, args, error_result)
            results[f'{tool_name}_error'] = str(e)
    
    return results

