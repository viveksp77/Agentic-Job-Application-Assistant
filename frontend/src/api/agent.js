import axios from 'axios';

const BASE = 'http://localhost:5000/api';
const PYTHON = 'http://localhost:8000';

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
// SSE streaming helpers
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