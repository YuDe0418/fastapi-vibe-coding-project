import { useEffect, useRef, useState } from 'react';
import { Heart } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { api, json } from '@/services/api';
import type { LikeState, Post } from '@/types';

export function formatLikes(count: number) {
  if (count < 1000) return String(count);
  const divisor = count < 1000000 ? 1000 : 1000000;
  return (Math.floor(count / divisor * 10) / 10).toFixed(1).replace(/\.0$/, '') + (divisor === 1000 ? 'K' : 'M');
}

export function LikeButton({ post }: { post: Post }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [state, setState] = useState<LikeState>({ like_count: post.like_count ?? 0, real_like_count: post.real_like_count ?? 0, demo_like_count: post.demo_like_count ?? 0, liked_by_me: Boolean(user && post.liked_by_me) });
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  useEffect(() => {
    setState({ like_count: post.like_count ?? 0, real_like_count: post.real_like_count ?? 0, demo_like_count: post.demo_like_count ?? 0, liked_by_me: Boolean(user && post.liked_by_me) });
  }, [post.id, post.like_count, post.real_like_count, post.demo_like_count, post.liked_by_me, user?.id]);
  useEffect(() => {
    const update = (event: Event) => {
      const value = (event as CustomEvent<LikeState & { post_id: number }>).detail;
      if (value.post_id === post.id) setState({ ...value, liked_by_me: Boolean(user && value.liked_by_me) });
    };
    window.addEventListener('post-likes-changed', update);
    return () => window.removeEventListener('post-likes-changed', update);
  }, [post.id, user?.id]);
  const toggle = async () => {
    if (!user) { navigate('/login', { state: { from: location.pathname + location.search } }); return; }
    if (user.must_change_password) { navigate('/profile'); return; }
    if (pending.current) return;
    pending.current = true; setBusy(true);
    try {
      const next = await api<LikeState & { post_id: number }>(`/posts/${post.id}/likes`, json(state.liked_by_me ? 'DELETE' : 'POST'));
      setState(next);
      window.dispatchEvent(new CustomEvent('post-likes-changed', { detail: next }));
    } catch (error) { toast.error((error as Error).message); }
    finally { pending.current = false; setBusy(false); }
  };
  const title = `${state.like_count.toLocaleString()} 個愛心`;
  return <span className="like-control"><button type="button" className={`thread-action like-button ${state.liked_by_me ? 'liked' : ''}`} aria-label={state.liked_by_me ? '取消愛心' : '按愛心'} aria-pressed={state.liked_by_me} disabled={busy || (post.is_expired && !state.liked_by_me)} title={post.is_expired && !state.liked_by_me ? '文章已過期，無法新增愛心' : title} onClick={toggle}><Heart size={20} strokeWidth={1.6}/><span>{formatLikes(state.like_count)}</span></button></span>;
}
