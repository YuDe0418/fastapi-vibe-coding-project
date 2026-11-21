import { Link, Navigate, useLocation } from 'react-router-dom';
import { Pin, LoaderCircle, MessageSquare, Share2, Inbox, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { ApiError } from '@/services/api';
import type { Post } from '@/types';
import { date, relativeTime } from '@/lib/utils';
import { toast } from 'sonner';
import { LikeButton } from './LikeButton';
export function Loading() { return <div role="status" className="state"><LoaderCircle className="animate-spin"/><span>正在載入…</span></div>; }
export function Empty({ text = '這裡還很安靜，成為第一個分享的人吧。' }: { text?: string }) { return <div className="state"><Inbox size={36}/><h3>還沒有內容</h3><p className="muted">{text}</p></div>; }
export function ErrorState({ error, retry }: { error: Error; retry?: () => void }) { const code = error instanceof ApiError ? error.status : null; return <div role="alert" className="state"><AlertCircle/><h2>{code ? `${code} · ` : ''}{error.message}</h2>{retry && <Button variant="outline" onClick={retry}>重新載入</Button>}</div>; }
export function StatusPage({ code }: { code: number }) { return <div className="state py-24"><span className="eyebrow">COMMON GROUND</span><h1 className="text-6xl font-bold">{code}</h1><p>{code === 403 ? '你沒有瀏覽此頁面的權限' : code === 401 ? '請先登入後繼續' : '找不到這個頁面'}</p><Button asChild><Link to={code === 401 ? '/login' : '/'}>{code === 401 ? '前往登入' : '回到交流廣場'}</Link></Button></div>; }
export function Protected({ children, admin = false }: { children: React.ReactNode; admin?: boolean }) { const { user, loading } = useAuth(); const location = useLocation(); if (loading) return <Loading/>; if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace/>; if (user.must_change_password && location.pathname !== '/profile') return <Navigate to="/profile" replace/>; if (admin && !user.is_admin) return <StatusPage code={403}/>; return <>{children}</>; }
export function PostCard({ post }: { post: Post }) {
 const share = async () => {
  try {
   await navigator.clipboard.writeText(new URL(`/posts/${post.id}`, window.location.origin).href);
   toast.success('貼文連結已複製');
  } catch { toast.error('無法自動複製，請開啟貼文後複製網址'); }
 };
 const duplicateTitle = post.content.split('\n')[0].slice(0,160) === post.title;
 return <article className="thread-post">
  <div className="thread-avatar-column"><div className="avatar thread-avatar">{post.author_name.slice(0,1)}</div><span className="thread-line"/></div>
  <div className="thread-main"><header className="thread-meta"><strong>{post.author_name}</strong><span className="meta-dot">·</span><time dateTime={post.created_at} title={date(post.created_at)}>{relativeTime(post.created_at)}</time>{post.is_pinned && <span className="pinned-label ml-auto"><Pin size={11}/>置頂</span>}{post.is_expired && <span className="badge badge-muted ml-auto">已過期</span>}</header>
   <Link to={`/posts/${post.id}`} className="thread-body">{!duplicateTitle && <h3>{post.title}</h3>}<p>{post.content}</p></Link>
   <div className="thread-actions"><LikeButton post={post}/><Link to={`/posts/${post.id}`} className="thread-action" aria-label={`回覆 ${post.title}，${post.reply_count} 則回覆`}><MessageSquare size={19} strokeWidth={1.6}/><span>{post.reply_count}</span></Link><button type="button" className="thread-action" aria-label={`分享 ${post.title}`} onClick={share}><Share2 size={18} strokeWidth={1.6}/></button><Link className="thread-read" to={`/posts/${post.id}`}>查看對話 <span aria-hidden="true">↗</span></Link></div>
  </div>
 </article>;
}
export function Pagination({ page, total, size, onChange }: { page: number; total: number; size: number; onChange: (page: number) => void }) { const pages = Math.max(1, Math.ceil(total / size)); return <div className="pagination"><span className="muted text-sm">共 {total} 筆 · 第 {page} / {pages} 頁</span><div className="flex gap-2"><Button variant="outline" size="icon" aria-label="上一頁" disabled={page <= 1} onClick={() => onChange(page - 1)}><ChevronLeft size={17}/></Button><Button variant="outline" size="icon" aria-label="下一頁" disabled={page >= pages} onClick={() => onChange(page + 1)}><ChevronRight size={17}/></Button></div></div>; }
