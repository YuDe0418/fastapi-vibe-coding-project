import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Protected, PostCard, Pagination } from './components/common';
import { AuthPage } from './pages/Auth';
import { Home } from './pages/Home';
import { Confirm } from './components/ui/confirm';
import { Button } from './components/ui/button';
import type { User, Post } from './types';
const user: User = { id: 1, username: 'alice', nickname: 'Alice', email: 'alice@example.com', phone: '', address: '', is_admin: false, must_change_password: false, created_at: '2026-01-01T00:00:00Z' };
const response = (data: unknown, status = 200) => ({ ok: status < 400, status, json: async () => data }) as Response;
beforeEach(() => { vi.restoreAllMocks(); });
function wrap(node: React.ReactNode) { return render(<MemoryRouter><AuthProvider>{node}</AuthProvider></MemoryRouter>); }
describe('authentication and authorization', () => {
 it('completes login using cookies and logs out', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_url, options) => {
   if (String(_url).endsWith('/me')) return response({ detail: 'unauthorized' }, 401);
   if (String(_url).endsWith('/login')) return response(user);
   return response(null, 204);
  });
  function Session() { const auth = useAuth(); return <><span>{auth.user?.nickname || 'Guest'}</span><button onClick={auth.logout}>Logout</button></>; }
  wrap(<><AuthPage/><Session/></>);
  await userEvent.type(screen.getByLabelText('帳號'), 'alice');
  await userEvent.type(screen.getByLabelText('密碼'), 'safe-password-123');
  await userEvent.click(screen.getByRole('button', { name: '登入' }));
  await screen.findByText('Alice');
  expect(fetchMock).toHaveBeenCalledWith('/api/users/login', expect.objectContaining({ credentials: 'include', method: 'POST' }));
  await userEvent.click(screen.getByText('Logout'));
  await screen.findByText('Guest');
 });
 it('rejects non-admin users from admin content', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(user));
  wrap(<Protected admin><div>Secret admin</div></Protected>);
  await screen.findByText('403');
  expect(screen.queryByText('Secret admin')).not.toBeInTheDocument();
 });
 it('allows admin users', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(response({ ...user, is_admin: true }));
  wrap(<Protected admin><div>Secret admin</div></Protected>);
  await screen.findByText('Secret admin');
 });
 it('redirects guests to login', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(response({}, 401));
  wrap(<Routes><Route path="/" element={<Protected admin>Secret</Protected>}/><Route path="/login" element={<div>Login destination</div>}/></Routes>);
  await screen.findByText('Login destination');
 });
 it('forces password reset before protected content', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(response({ ...user, must_change_password: true }));
  wrap(<Routes><Route path="/" element={<Protected>Content</Protected>}/><Route path="/profile" element={<div>Password settings</div>}/></Routes>);
  await screen.findByText('Password settings');
 });
});
describe('important components', () => {
 it('renders a real post and reply count', () => {
  const post: Post = { id: 3, author_id: 1, author_name: 'Alice', title: 'Real discussion', content: 'Hello', remarks: '', created_at: user.created_at, expires_at: '2030-01-01T00:00:00Z', is_expired: false, like_count: 0, real_like_count: 0, demo_like_count: 0, liked_by_me: false, reply_count: 4 };
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(user));
  wrap(<PostCard post={post}/>);
  expect(screen.getByRole('link', { name: /Real discussion Hello/ })).toHaveAttribute('href', '/posts/3');
  expect(screen.getByText('4')).toBeInTheDocument();
 });
 it('paginates and disables previous at first page', async () => {
  const change = vi.fn(); render(<Pagination page={1} total={20} size={9} onChange={change}/>);
  expect(screen.getByLabelText('上一頁')).toBeDisabled();
  await userEvent.click(screen.getByLabelText('下一頁')); expect(change).toHaveBeenCalledWith(2);
 });
 it('requires confirmation before deletion', async () => {
  const remove = vi.fn().mockResolvedValue(undefined);
  render(<Confirm title="Delete post?" description="Cannot undo" onConfirm={remove}><Button>Delete</Button></Confirm>);
  await userEvent.click(screen.getByText('Delete')); expect(remove).not.toHaveBeenCalled();
  await userEvent.click(screen.getByText('取消')); expect(remove).not.toHaveBeenCalled();
  await userEvent.click(screen.getByText('Delete')); await userEvent.click(screen.getByText('確認刪除'));
  await waitFor(() => expect(remove).toHaveBeenCalledOnce());
 });
});

describe('feed interactions', () => {
 it('publishes a real request from the quick composer and refreshes the feed', async () => {
  let published = false;
  const post: Post = { id: 31, author_id: 1, author_name: 'Alice', title: '今天的想法', content: '今天的想法\n一起聊聊', remarks: '', created_at: new Date().toISOString(), expires_at: '2030-01-01T00:00:00Z', is_expired: false, like_count: 0, real_like_count: 0, demo_like_count: 0, liked_by_me: false, reply_count: 0 };
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options) => {
   if (String(url).endsWith('/users/me')) return response(user);
   if (String(url) === '/api/posts' && options?.method === 'POST') { published = true; return response(post, 201); }
   return response({ items: published ? [post] : [], total: published ? 1 : 0, page: 1, page_size: 10 });
  });
  wrap(<Home/>);
  const composer = await screen.findByLabelText('分享你的想法');
  const publishButton = screen.getByRole('button', { name: '發布' });
  expect(publishButton).toBeDisabled();
  await userEvent.type(composer, '今天的想法{enter}一起聊聊');
  await userEvent.click(publishButton);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/posts', expect.objectContaining({ method: 'POST', body: JSON.stringify({ title: '今天的想法', content: '今天的想法\n一起聊聊' }), credentials: 'include' })));
  await waitFor(() => expect(composer).toHaveValue(''));
  expect(await screen.findByRole('link', { name: /^今天的想法\s*一起聊聊$/ })).toHaveAttribute('href', '/posts/31');
 });
 it('copies the actual post URL when sharing', async () => {
  const ui = userEvent.setup();
  const copy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
  const post: Post = { id: 17, author_id: 1, author_name: 'Alice', title: 'Shareable', content: 'Hello', remarks: '', created_at: user.created_at, expires_at: '2030-01-01T00:00:00Z', is_expired: false, like_count: 0, real_like_count: 0, demo_like_count: 0, liked_by_me: false, reply_count: 0 };
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(user));
  wrap(<PostCard post={post}/>);
  await ui.click(screen.getByRole('button', { name: '分享 Shareable' }));
  expect(copy).toHaveBeenCalledWith(new URL('/posts/17', window.location.origin).href);
 });
});
