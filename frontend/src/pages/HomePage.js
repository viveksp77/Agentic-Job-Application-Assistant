import React, { useState } from 'react';
import { analyzeApplication, scrapeJobUrl } from '../api/agent';
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

export default function HomePage({
  persistedResults,
  setPersistedResults,
  persistedLoading,
  setPersistedLoading,
}) {
  const [resumeFile, setResumeFile]   = useState(null);
  const [jobDesc, setJobDesc]         = useState('');
  const [jobUrl, setJobUrl]           = useState('');
  const [scraping, setScraping]       = useState(false);
  const [scrapeError, setScrapeError] = useState('');
  const [progress, setProgress]       = useState(0);
  const [error, setError]             = useState('');
  const [dragging, setDragging]       = useState(false);

  // Use lifted state from App.js
  const loading  = persistedLoading;
  const results  = persistedResults;
  const setLoading = setPersistedLoading;
  const setResults = setPersistedResults;

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file?.type === 'application/pdf') setResumeFile(file);
  };

  const handleScrape = async () => {
    if (!jobUrl.trim()) return;
    setScraping(true);
    setScrapeError('');
    try {
      const data = await scrapeJobUrl(jobUrl.trim());
      if (data.success) {
        setJobDesc(data.job_description);
        setScrapeError('');
      } else {
        setScrapeError(data.error || 'Could not extract job description.');
      }
    } catch (err) {
      setScrapeError(err.response?.data?.error || err.message || 'Scrape failed.');
    } finally {
      setScraping(false);
    }
  };

  const handleSubmit = async () => {
    if (!resumeFile || !jobDesc.trim()) {
      setError('Please upload a resume and provide a job description.');
      return;
    }
    setError('');
    setLoading(true);
    setResults(null);
    setProgress(0);

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

  const handleReset = () => {
    setResults(null);
    setResumeFile(null);
    setJobDesc('');
    setJobUrl('');
    setScrapeError('');
    setProgress(0);
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
              <input id="file-input" type="file" accept=".pdf" className="file-input"
                onChange={(e) => setResumeFile(e.target.files[0])} />
            </div>

            {/* Job description */}
            <div className="form-card">
              <span className="form-label">Job Description</span>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <input
                  style={{
                    flex: 1, padding: '0.6rem 0.75rem',
                    background: 'var(--bg3)', border: '1px solid var(--border2)',
                    borderRadius: 8, color: 'var(--text)', fontFamily: 'inherit',
                    fontSize: '0.85rem', outline: 'none',
                  }}
                  placeholder="Paste job URL to auto-fetch (optional)"
                  value={jobUrl}
                  onChange={(e) => setJobUrl(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleScrape()}
                />
                <button
                  onClick={handleScrape}
                  disabled={scraping || !jobUrl.trim()}
                  style={{
                    padding: '0.6rem 1rem',
                    background: scraping ? 'var(--bg3)' : 'var(--accent)',
                    border: 'none', borderRadius: 8,
                    color: 'white', fontFamily: 'inherit',
                    fontSize: '0.85rem', cursor: 'pointer',
                    whiteSpace: 'nowrap', transition: 'all 0.15s',
                    opacity: (!jobUrl.trim() || scraping) ? 0.5 : 1,
                  }}
                >
                  {scraping ? '⏳' : '🔗 Fetch'}
                </button>
              </div>

              {scrapeError && (
                <div style={{
                  fontSize: '0.8rem', color: '#f87171',
                  background: 'rgba(239,68,68,0.08)',
                  border: '1px solid rgba(239,68,68,0.2)',
                  borderRadius: 6, padding: '0.5rem 0.75rem', marginBottom: 8,
                }}>
                  {scrapeError}
                </div>
              )}

              {jobDesc && !scrapeError && jobUrl && (
                <div style={{ fontSize: '0.78rem', color: '#34d399', marginBottom: 6 }}>
                  ✓ Job description fetched successfully
                </div>
              )}

              <textarea
                className="textarea"
                placeholder="Or paste the job description here..."
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

      {loading && <ProgressBar steps={STEPS} currentStep={progress} />}

      {results && (
        <>
          <ResultTabs results={results} />
          <button
            className="submit-btn"
            style={{ marginTop: '1rem' }}
            onClick={handleReset}
          >
            ← Analyse Another
          </button>
        </>
      )}
    </div>
  );
}