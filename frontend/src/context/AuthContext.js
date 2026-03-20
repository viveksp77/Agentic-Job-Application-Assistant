import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);
const BASE = process.env.REACT_APP_API_URL || 'https://agentic-job-application-assistant-production.up.railway.app/api';

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore session from localStorage on mount
  useEffect(() => {
    const token    = localStorage.getItem('token');
    const username = localStorage.getItem('username');
    const email    = localStorage.getItem('email');
    if (token && username) {
      setUser({ token, username, email });
    }
    setLoading(false);
  }, []);

  const register = async (email, username, password) => {
    const res = await axios.post(`${BASE}/auth/register`, { email, username, password });
    const { access_token, username: uname, email: uemail } = res.data;
    localStorage.setItem('token', access_token);
    localStorage.setItem('username', uname);
    localStorage.setItem('email', uemail);
    setUser({ token: access_token, username: uname, email: uemail });
    return res.data;
  };

  const login = async (username, password) => {
    const res = await axios.post(`${BASE}/auth/login`, { username, password });
    const { access_token, username: uname, email: uemail } = res.data;
    localStorage.setItem('token', access_token);
    localStorage.setItem('username', uname);
    localStorage.setItem('email', uemail);
    setUser({ token: access_token, username: uname, email: uemail });
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('email');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, register, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);