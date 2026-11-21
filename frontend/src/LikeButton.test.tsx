import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LikeButton, formatLikes } from './components/LikeButton';
import type { Post } from './types';

const user = { id: 1, username: 'alice', nickname: 'Alice', email: 'alice@example.com', phone: '', address: '', is_admin: false, must_change_password: false, created_at: '2026-01-01T00:00:00Z' };
const post: Post = { id: 1, author_id: 1, author_name: 'Alice', title: 'Hello', content: 'Hello', remarks: '', created_at: user.created_at, expires_at: '2030-01-01T00:00:00Z', is_expired: false, reply_count: 0, like_count: 24300, real_like_count: 0, demo_like_count: 24300, liked_by_me: false };
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body }) as Response;
function Ready() { const { loading } = useAuth(); return loading ? null : <span>Session ready</span>; }
function wrap() { render(<MemoryRouter><AuthProvider><Ready/><Routes><Route path="/" element={<LikeButton post={post}/>}/><Route path="/login" element={<span>Login destination</span>}/></Routes></AuthProvider></MemoryRouter>); }
beforeEach(() => { vi.restoreAllMocks(); });

describe('heart interaction', () => {
 it('formats the requested demonstration values', () => {
  expect(formatLikes(24300)).toBe('24.3K');
  expect(formatLikes(45800)).toBe('45.8K');
  expect(formatLikes(999)).toBe('999');
  expect(formatLikes(1000)).toBe('1K');
 });
 it('likes and unlikes using server totals without an inline demonstration label', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options) => {
   if (String(url).endsWith('/users/me')) return response(user);
   const liked = options?.method === 'POST';
   return response({ post_id: 1, like_count: 24300 + Number(liked), real_like_count: Number(liked), demo_like_count: 24300, liked_by_me: liked });
  });
  wrap(); await screen.findByText('Session ready');
  expect(screen.getByText('24.3K')).toBeInTheDocument();
  expect(screen.queryByText('含展示數')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: '按愛心' }));
  const unlike = await screen.findByRole('button', { name: '取消愛心' });
  expect(unlike).toHaveAttribute('aria-pressed', 'true');
  expect(unlike.getAttribute('title')).toContain('24,301');
  expect(fetchMock).toHaveBeenCalledWith('/api/posts/1/likes', expect.objectContaining({ method: 'POST', credentials: 'include' }));
  await userEvent.click(unlike);
  await waitFor(() => expect(screen.getByRole('button', { name: '按愛心' })).toHaveAttribute('aria-pressed', 'false'));
  expect(fetchMock).toHaveBeenCalledWith('/api/posts/1/likes', expect.objectContaining({ method: 'DELETE' }));
 });
 it('takes an anonymous visitor to login without sending a like', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response({ detail: 'Please login' }, 401));
  wrap(); await screen.findByText('Session ready');
  await userEvent.click(screen.getByRole('button', { name: '按愛心' }));
  await screen.findByText('Login destination');
  expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/likes'))).toBe(false);
 });
 it('does not show a false successful like on API errors', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async url => String(url).endsWith('/users/me') ? response(user) : response({ detail: 'Unavailable' }, 500));
  wrap(); await screen.findByText('Session ready');
  await userEvent.click(screen.getByRole('button', { name: '按愛心' }));
  await waitFor(() => expect(screen.getByRole('button', { name: '按愛心' })).toBeEnabled());
  expect(screen.getByRole('button', { name: '按愛心' })).toHaveAttribute('aria-pressed', 'false');
  expect(screen.getByText('24.3K')).toBeInTheDocument();
 });
});
