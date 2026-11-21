import { useSearchParams, Link } from 'react-router-dom';
import { Search, ArrowUpRight, ArrowRight, X, MessageSquare, Hash, CornerDownLeft, Plus } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { useResource } from '@/hooks/useResource';
import type { Page, Post } from '@/types';
import { Loading, ErrorState, Empty, PostCard, Pagination } from '@/components/common';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { api, json } from '@/services/api';

export function Home({ mine = false }: { mine?: boolean }) {
  const [params, setParams] = useSearchParams();
  const q = params.get('q') || '';
  const page = Math.max(1, Number(params.get('page')) || 1);
  const sort = params.get('sort') === 'popular' ? 'popular' : 'latest';
  const searching = params.get('search') === '1';
  const [search, setSearch] = useState(q);
  const [draft, setDraft] = useState('');
  const [posting, setPosting] = useState(false);
  const [postError, setPostError] = useState('');
  const searchInput = useRef<HTMLInputElement>(null);
  const { user } = useAuth();
  const resource = useResource<Page<Post>>(`/posts${mine ? '/mine' : ''}?q=${encodeURIComponent(q)}&page=${page}&page_size=10&sort=${sort}`);
  const popular = useResource<Page<Post>>('/posts?sort=popular&page_size=4');
  useEffect(() => { setSearch(q); }, [q]);
  useEffect(() => { if (searching) searchInput.current?.focus(); }, [searching]);
  const change = (values: Record<string,string>) => setParams({ q, sort, ...(searching ? { search: '1' } : {}), ...values });
  const publish = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!draft.trim() || posting) return;
    setPosting(true); setPostError('');
    try {
      const content = draft.trim();
      await api<Post>('/posts', json('POST', { title: content.split('\n')[0].slice(0,160), content }));
      setDraft('');
      setParams({ sort: 'latest' });
      resource.reload(); popular.reload();
      toast.success('貼文已發布');
    } catch (error) { setPostError((error as Error).message); }
    finally { setPosting(false); }
  };
  return <div className="feed-layout">
    <section className="feed-column" aria-label={mine ? '我的貼文' : '動態牆'}>
      <div className="feed-heading"><div><span className="eyebrow">{mine ? 'YOUR SPACE' : 'THE FEED'}</span><h1>{mine ? '我的貼文' : searching ? '搜尋想法' : '此刻，聊點什麼'}<span className="orange-period">.</span></h1></div><span className="feed-label"><span className="status-dot"/>交流中</span></div>
      <div className="feed-surface">
        <div className="feed-tabs" aria-label="貼文排序"><button className={sort === 'latest' ? 'active' : ''} aria-pressed={sort === 'latest'} onClick={() => change({ sort: 'latest', page: '1' })}>最新動態</button><button className={sort === 'popular' ? 'active' : ''} aria-pressed={sort === 'popular'} onClick={() => change({ sort: 'popular', page: '1' })}>熱門討論</button><span className="feed-total">{resource.data ? `${resource.data.total} 則貼文` : '—'}</span></div>
        {!mine && <div className="composer"><div className="avatar composer-avatar">{user ? user.nickname.slice(0,1) : <Plus size={20}/>}</div>{user && !user.must_change_password ? <form onSubmit={publish} className="composer-form"><label className="sr-only" htmlFor="quick-post">分享你的想法</label><textarea id="quick-post" rows={draft ? 3 : 1} maxLength={20000} value={draft} onChange={e => setDraft(e.target.value)} placeholder="有什麼新鮮事？" disabled={posting}/><div className="composer-bottom"><span className="composer-hint">一個念頭，也值得分享。</span><Button size="sm" disabled={!draft.trim() || posting} type="submit">{posting ? '發布中…' : '發布'}<ArrowUpRight size={14}/></Button></div>{postError && <p role="alert" className="form-error mt-3">{postError}</p>}</form> : <div className="composer-guest"><Link to={user ? '/profile' : '/login'}>{user ? '先更新密碼，再加入對話。' : '有什麼新鮮事？'}</Link><Button size="sm" variant="outline" asChild><Link to={user ? '/profile' : '/login'}>{user ? '修改密碼' : '發文'}</Link></Button></div>}</div>}
        <form className="feed-search" onSubmit={e => { e.preventDefault(); change({ q: search.trim(), page: '1' }); }}><Search size={17}/><input ref={searchInput} aria-label="搜尋文章" placeholder="搜尋貼文、想法或作者" value={search} onChange={e => setSearch(e.target.value)}/>{search && <button type="button" aria-label="清除搜尋" onClick={() => { setSearch(''); change({ q: '', page: '1' }); }}><X size={15}/></button>}<button type="submit" aria-label="執行搜尋"><CornerDownLeft size={16}/></button></form>
        {q && <div className="search-summary">搜尋「{q}」<span>{resource.data?.total ?? '—'} 則結果</span></div>}
        {resource.loading ? <Loading/> : resource.error ? <ErrorState error={resource.error} retry={resource.reload}/> : !resource.data?.items.length ? <div className="feed-empty"><Empty text={q ? '沒有找到相關貼文，換個關鍵字試試？' : mine ? '你的第一個想法，就從這裡開始。' : '廣場還很安靜。今天有什麼想說的？'}/>{!q && <Button variant="outline" asChild><Link to={user?.must_change_password ? '/profile' : user ? '/posts/new' : '/login'}><Plus size={16}/>寫下第一則貼文</Link></Button>}</div> : <div className="thread-list">{resource.data.items.map(post => <PostCard key={post.id} post={post}/>)}</div>}
        {resource.data && resource.data.total > 10 && <Pagination page={page} total={resource.data.total} size={10} onChange={p => change({ page: String(p) })}/>}
        {!resource.loading && !resource.error && !!resource.data?.items.length && <div className="feed-end"><span/>你已看完這一頁的動態<span/></div>}
      </div>
    </section>
    <aside className="feed-sidebar" aria-label="廣場資訊">
      <section className="intro-block"><span className="eyebrow"><span className="tiny-square"/> COMMON GROUND</span><h2>想法沒有標準答案。<br/><span>聊聊，就有可能。</span></h2><p>日常、靈感，或還沒想好的問題。<br/>這裡是你我對話的共同空間。</p>{!user && <Button asChild className="w-full"><Link to="/register">加入這場對話<ArrowUpRight size={16}/></Link></Button>}{user && <Link className="sidebar-own-link" to="/my-posts">查看我的貼文<ArrowUpRight size={16}/></Link>}</section>
      <section className="trending-block"><div className="sidebar-title"><h2><Hash size={17}/>正在討論</h2><span>ON THE BOARD</span></div>{popular.loading ? <p className="sidebar-note">載入討論中…</p> : popular.error ? <ErrorState error={popular.error} retry={popular.reload}/> : !popular.data?.items.length ? <div className="sidebar-note"><MessageSquare size={22}/><p>新的話題，從你開始。</p><Link to={user ? '/posts/new' : '/login'}>分享一個想法<ArrowRight size={13}/></Link></div> : popular.data.items.map((post,i) => <Link key={post.id} to={`/posts/${post.id}`} className="trending-item"><span className="trending-index">{String(i+1).padStart(2,'0')}</span><div><strong>{post.title}</strong><small>{post.reply_count} 則回覆 · {post.author_name}</small></div><ArrowUpRight size={14}/></Link>)}</section>
      <section className="community-note"><span className="note-symbol" aria-hidden="true">✳</span><h3>好的對話，從尊重開始。</h3><p>真實分享，友善回應。<br/>不同的觀點，讓廣場更有意思。</p><span className="eyebrow">LESS NOISE. MORE CONVERSATION.</span></section>
      <div className="sidebar-footer"><span>Common Ground</span><span>文字連結彼此。</span></div>
    </aside>
  </div>;
}
