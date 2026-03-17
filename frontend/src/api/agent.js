import axios from 'axios';

const BASE = 'http://localhost:5000/api';

// ---------------------------------------------------------------------------
// Resume analysis
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Application history
// ---------------------------------------------------------------------------
export const getHistory = async () => {
  const response = await axios.get(`${BASE}/history`, { timeout: 10000 });
  return response.data;
};

// ---------------------------------------------------------------------------
// Interview simulator
// ---------------------------------------------------------------------------
export const getInterviewQuestion = async (jobRole, difficulty, conversation, questionNumber) => {
  const response = await axios.post(
    `${BASE}/interview/question`,
    {
      job_role: jobRole,
      difficulty,
      conversation,
      question_number: questionNumber,
    },
    { timeout: 60000 }
  );
  return response.data;
};

export const evaluateAnswer = async (jobRole, difficulty, conversation, userAnswer) => {
  const response = await axios.post(
    `${BASE}/interview/evaluate`,
    {
      job_role: jobRole,
      difficulty,
      conversation,
      user_answer: userAnswer,
    },
    { timeout: 60000 }
  );
  return response.data;
};