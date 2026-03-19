import axios from 'axios';

const BASE   = process.env.REACT_APP_API_URL    || 'http://localhost:5000/api';
const PYTHON = process.env.REACT_APP_PYTHON_URL || 'http://localhost:8000';

export const analyzeApplication = async (resumeFile, jobDesc) => {
  const form = new FormData();
  form.append('resume', resumeFile);
  form.append('job_desc', jobDesc);
  const response = await axios.post(`${BASE}/analyze`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  });
  return response.data;
};

export const getHistory = async () => {
  const response = await axios.get(`${BASE}/history`, { timeout: 10000 });
  return response.data;
};

export const getInterviewQuestion = async (jobRole, difficulty, conversation, questionNumber) => {
  const response = await axios.post(`${BASE}/interview/question`, {
    job_role: jobRole, difficulty, conversation, question_number: questionNumber,
  }, { timeout: 60000 });
  return response.data;
};

export const evaluateAnswer = async (jobRole, difficulty, conversation, userAnswer) => {
  const response = await axios.post(`${BASE}/interview/evaluate`, {
    job_role: jobRole, difficulty, conversation, user_answer: userAnswer,
  }, { timeout: 60000 });
  return response.data;
};

// ---------------------------------------------------------------------------
// SSE streaming helpers — go directly to Python (bypasses Node)
// ---------------------------------------------------------------------------

const _stream = (url, payload, onToken, onDone, onError) => {
  const ctrl = new AbortController();

  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: ctrl.signal,
  })
    .then(async (res) => {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') { onDone(); return; }
            if (data.startsWith('[ERROR]')) { onError(data); return; }
            onToken(data.replace(/\\n/g, '\n'));
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err.message);
    });

  return () => ctrl.abort();
};

export const streamCoverLetter = (payload, onToken, onDone, onError) =>
  _stream(`${PYTHON}/stream/cover-letter`, payload, onToken, onDone, onError);

export const streamInterviewQuestions = (payload, onToken, onDone, onError) =>
  _stream(`${PYTHON}/stream/interview-questions`, payload, onToken, onDone, onError);

export const scrapeJobUrl = async (url) => {
  const response = await axios.post(`${BASE}/scrape`, { url }, { timeout: 30000 });
  return response.data;
};

// PDF export — goes directly to Python FastAPI
export const downloadCoverLetterPDF = async (payload) => {
  const response = await fetch(`${PYTHON}/export/cover-letter-pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'cover_letter.pdf';
  a.click();
  URL.revokeObjectURL(url);
};

export const downloadResumePDF = async (payload) => {
  const response = await fetch(`${PYTHON}/export/resume-pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'optimized_resume.pdf';
  a.click();
  URL.revokeObjectURL(url);
};