import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export default function AuthPage() {
  const { login, register } = useAuth();
  const [mode, setMode]     = useState('login'); // 'login' | 'register'
  const [form, setForm]     = useState({ email: '', username: '', password: '' });
  const [error, setError]   = useState('');
  const [loading, setLoading] = useState(false);

  const update = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  const handleSubmit = async () => {
    setError('');
    if (!form.username || !form.password) {
      setError('Please fill in all required fields.');
      return;
    }
    if (mode === 'register' && !form.email) {
      setError('Email is required for registration.');
      return;
    }
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(form.username, form.password);
      } else {
        await register(form.email, form.username, form.password);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: '100%', padding: '0.75rem',
    background: 'var(--bg3)', border: '1px solid var(--border2)',
    borderRadius: 8, color: 'var(--text)',
    fontFamily: 'inherit', fontSize: '0.95rem', outline: 'none',
    boxSizing: 'border-box',
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg)',
    }}>
      <div style={{
        width: '100%', maxWidth: 420,
        background: 'var(--bg2)', border: '1px solid var(--border)',
        borderRadius: 16, padding: '2.5rem',
        display: 'flex', flexDirection: 'column', gap: '1.25rem',
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 8 }}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>⚡</div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, letterSpacing: '-0.03em', margin: 0 }}>
            JobAgent AI
          </h1>
          <p style={{ color: 'var(--muted)', fontSize: '0.9rem', marginTop: 6 }}>
            {mode === 'login' ? 'Sign in to your account' : 'Create your free account'}
          </p>
        </div>

        {/* Mode toggle */}
        <div style={{ display: 'flex', background: 'var(--bg3)', borderRadius: 8, padding: 4 }}>
          {['login', 'register'].map(m => (
            <button key={m} onClick={() => { setMode(m); setError(''); }}
              style={{
                flex: 1, padding: '0.5rem',
                background: mode === m ? 'var(--accent)' : 'transparent',
                border: 'none', borderRadius: 6,
                color: mode === m ? 'white' : 'var(--muted)',
                fontFamily: 'inherit', fontSize: '0.9rem',
                cursor: 'pointer', transition: 'all 0.15s',
                textTransform: 'capitalize',
              }}>
              {m}
            </button>
          ))}
        </div>

        {/* Fields */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {mode === 'register' && (
            <input style={inputStyle} type="email" placeholder="Email address"
              value={form.email} onChange={e => update('email', e.target.value)} />
          )}
          <input style={inputStyle} type="text" placeholder="Username"
            value={form.username} onChange={e => update('username', e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()} />
          <input style={inputStyle} type="password"
            placeholder={mode === 'register' ? 'Password (min 6 chars)' : 'Password'}
            value={form.password} onChange={e => update('password', e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()} />
        </div>

        {error && (
          <div style={{
            background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)',
            color: '#f87171', borderRadius: 8, padding: '0.75rem',
            fontSize: '0.85rem',
          }}>
            {error}
          </div>
        )}

        <button
          onClick={handleSubmit} disabled={loading}
          style={{
            padding: '0.9rem', background: 'var(--accent)',
            border: 'none', borderRadius: 8,
            color: 'white', fontFamily: 'inherit',
            fontSize: '1rem', fontWeight: 500,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
            transition: 'all 0.15s',
          }}>
          {loading ? '...' : mode === 'login' ? 'Sign in' : 'Create account'}
        </button>

        <p style={{ textAlign: 'center', fontSize: '0.85rem', color: 'var(--muted)', margin: 0 }}>
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <span onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
            style={{ color: 'var(--accent2)', cursor: 'pointer' }}>
            {mode === 'login' ? 'Sign up' : 'Sign in'}
          </span>
        </p>
      </div>
    </div>
  );
}