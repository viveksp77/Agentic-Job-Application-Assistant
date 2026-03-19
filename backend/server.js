const express = require('express');
const cors = require('cors');
const axios = require('axios');
const multer = require('multer');
const FormData = require('form-data');
const fs = require('fs');

const app = express();
const upload = multer({ dest: 'uploads/' });

app.use(cors());
app.use(express.json());

const PYTHON_API = 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Resume analysis
// ---------------------------------------------------------------------------
app.post('/api/analyze', upload.single('resume'), async (req, res) => {
    try {
        const form = new FormData();
        form.append('resume', fs.createReadStream(req.file.path), req.file.originalname);
        form.append('job_desc', req.body.job_desc);

        const response = await axios.post(`${PYTHON_API}/analyze`, form, {
            headers: form.getHeaders(),
            timeout: 300000,
        });

        fs.unlinkSync(req.file.path);
        res.json(response.data);
    } catch (err) {
        console.error('Analyze error:', err.message);
        res.status(500).json({ error: err.message });
    }
});

// ---------------------------------------------------------------------------
// Application history
// ---------------------------------------------------------------------------
app.get('/api/history', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_API}/history`, { timeout: 10000 });
        res.json(response.data);
    } catch (err) {
        console.error('History error:', err.message);
        res.status(500).json({ error: err.message });
    }
});

// ---------------------------------------------------------------------------
// Interview simulator — get next question
// ---------------------------------------------------------------------------
app.post('/api/interview/question', async (req, res) => {
    try {
        const response = await axios.post(
            `${PYTHON_API}/interview/question`,
            req.body,
            {
                headers: { 'Content-Type': 'application/json' },
                timeout: 60000,
            }
        );
        res.json(response.data);
    } catch (err) {
        console.error('Interview question error:', err.message);
        res.status(500).json({ error: err.message });
    }
});

// ---------------------------------------------------------------------------
// Interview simulator — evaluate answer
// ---------------------------------------------------------------------------
app.post('/api/interview/evaluate', async (req, res) => {
    try {
        const response = await axios.post(
            `${PYTHON_API}/interview/evaluate`,
            req.body,
            {
                headers: { 'Content-Type': 'application/json' },
                timeout: 60000,
            }
        );
        res.json(response.data);
    } catch (err) {
        console.error('Interview evaluate error:', err.message);
        res.status(500).json({ error: err.message });
    }
});

// Job scraper
app.post('/api/scrape', async (req, res) => {
    try {
        const response = await axios.post(`${PYTHON_API}/scrape`, req.body, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 30000,
        });
        res.json(response.data);
    } catch (err) {
        console.error('Scrape error:', err.message);
        res.status(500).json({ error: err.message });
    }
});

// Auth routes — proxy to Python
app.post('/api/auth/register', async (req, res) => {
    try {
        const response = await axios.post(`${PYTHON_API}/auth/register`, req.body, {
            headers: { 'Content-Type': 'application/json' }, timeout: 10000,
        });
        res.json(response.data);
    } catch (err) {
        res.status(err.response?.status || 500).json(err.response?.data || { error: err.message });
    }
});

app.post('/api/auth/login', async (req, res) => {
    try {
        const response = await axios.post(`${PYTHON_API}/auth/login`, req.body, {
            headers: { 'Content-Type': 'application/json' }, timeout: 10000,
        });
        res.json(response.data);
    } catch (err) {
        res.status(err.response?.status || 500).json(err.response?.data || { error: err.message });
    }
});

app.get('/api/auth/me', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_API}/auth/me`, {
            headers: { 'Authorization': req.headers.authorization }, timeout: 10000,
        });
        res.json(response.data);
    } catch (err) {
        res.status(err.response?.status || 500).json(err.response?.data || { error: err.message });
    }
});

// ---------------------------------------------------------------------------
// Start server
// ---------------------------------------------------------------------------
app.listen(5000, () => console.log('Node server running on port 5000'));