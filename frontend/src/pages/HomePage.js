import React, { useState } from 'react';
import { analyzeApplication } from '../api/agent';
import ProgressBar from '../components/ProgressBar';
import ResultTabs from '../components/ResultTabs';

const STEPS = [
  'Parse resume',
  'Analyse job description',
  'Extract resume skills',
  'Skill gap analysis',
  'Optimise resume',
  'Generate cover letter',
  'Generate interview questions',
  'Skill suggestions',
];

export default function HomePage() {
  const [resumeFile, setResumeFile] = useState(null);
  const [jobDesc, setJobDesc] = useState('');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file?.type === 'application/pdf') setResumeFile(file);
  };

  const handleSubmit = async () => {
    if (!resumeFile || !jobDesc.trim()) {
      setError('Please upload a resume and paste a job description.');
      return;
    }
    setError('');
    setLoading(true);
    setResults(null);
    setProgress(0);

    // Simulate step progress while API call runs
    let step = 0;
    const interval = setInterval(() => {
      step = Math.min(step + 1, STEPS.length - 1);
      setProgress(step);
    }, 3500);

    try {
      const data = await analyzeApplication(resumeFile, jobDesc);
      clearInterval(interval);
      setProgress(STEPS.length);
      setResults(data);
    } catch (err) {
      clearInterval(interval);
      setError(err.response?.data?.error || err.message || 'Analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-form">
      <div className="hero">
        <h1>Your AI <span>Job Application</span> Agent</h1>
        <p>Upload your resume and job description — the agent handles the rest.</p>
      </div>

      {!loading && !results && (
        <>
          <div className="form-grid">
            {/* Resume upload */}
            <div className="form-card">
              <span className="form-label">Resume (PDF)</span>
              <div
                className={`drop-zone ${dragging ? 'over' : ''} ${resumeFile ? 'filled' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-input').click()}
              >
                <div className="drop-icon">{resumeFile ? '✅' : '📄'}</div>
                <div className="drop-text">
                  <strong>{resumeFile ? resumeFile.name : 'Drop PDF here'}</strong>
                  {!resumeFile && 'or click to browse'}
                </div>
              </div>
              <input
                id="file-input"
                type="file"
                accept=".pdf"
                className="file-input"
                onChange={(e) => setResumeFile(e.target.files[0])}
              />
            </div>

            {/* Job description */}
            <div className="form-card">
              <span className="form-label">Job Description</span>
              <textarea
                className="textarea"
                placeholder="Paste the full job description here..."
                value={jobDesc}
                onChange={(e) => setJobDesc(e.target.value)}
              />
            </div>
          </div>

          {error && <div className="error-msg">{error}</div>}

          <button className="submit-btn" onClick={handleSubmit}>
            <span>⚡</span> Analyse Application
          </button>
        </>
      )}

      {loading && (
        <ProgressBar steps={STEPS} currentStep={progress} />
      )}

      {results && (
        <>
          <ResultTabs results={results} />
          <button
            className="submit-btn"
            style={{ marginTop: '1rem' }}
            onClick={() => { setResults(null); setResumeFile(null); setJobDesc(''); }}
          >
            ← Analyse Another
          </button>
        </>
      )}
    </div>
  );
}