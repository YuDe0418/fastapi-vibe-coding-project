import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider } from './contexts/AuthContext';
import App from './App';
import './index.css';
document.documentElement.classList.toggle('dark', localStorage.getItem('theme') !== 'light');
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><AuthProvider><App/><Toaster position="top-right" toastOptions={{ style: { background: 'var(--surface)', color: 'var(--ink)', border: '1px solid var(--line)' } }}/></AuthProvider></BrowserRouter></React.StrictMode>);
