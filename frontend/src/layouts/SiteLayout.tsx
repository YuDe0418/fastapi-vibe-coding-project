import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Home, Search, SquarePen, UserRound, Sun, Moon, LogOut, ShieldCheck, Layers2, ArrowUpRight } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';

export function SiteLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [dark, setDark] = useState(() => localStorage.getItem('theme') !== 'light');
  const searching = new URLSearchParams(location.search).get('search') === '1';
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  };
  const signOut = async () => {
    try { await logout(); toast.success('已登出'); navigate('/'); }
    catch (error) { toast.error((error as Error).message); }
  };
  return <div className="app-shell">
    <aside className="nav-rail" aria-label="主要導覽">
      <Link to="/" className="rail-logo" aria-label="Common Ground 首頁"><Layers2 size={30} strokeWidth={1.8}/></Link>
      <nav className="rail-links">
        <Link to="/" className={`rail-link ${location.pathname === '/' && !searching ? 'active' : ''}`} aria-label="首頁" title="首頁"><Home size={25} strokeWidth={1.7}/><span>首頁</span></Link>
        <Link to="/?search=1" className={`rail-link ${searching ? 'active' : ''}`} aria-label="搜尋" title="搜尋"><Search size={25} strokeWidth={1.7}/><span>搜尋</span></Link>
        <NavLink to={user ? '/posts/new' : '/login'} className="rail-link rail-compose" aria-label="發文" title="發文"><SquarePen size={24} strokeWidth={1.7}/><span>發文</span></NavLink>
        {user && <NavLink to="/my-posts" className="rail-link" aria-label="我的貼文" title="我的貼文"><Layers2 size={24} strokeWidth={1.7}/><span>貼文</span></NavLink>}
        <NavLink to={user ? '/profile' : '/login'} className="rail-link" aria-label={user ? '個人設定' : '登入帳號'} title={user ? '個人設定' : '登入帳號'}><UserRound size={25} strokeWidth={1.7}/><span>個人</span></NavLink>
      </nav>
      <div className="rail-bottom">
        {user?.is_admin && <NavLink to="/admin" className="rail-link" aria-label="管理後台" title="管理後台"><ShieldCheck size={22}/></NavLink>}
        <button className="rail-link" type="button" aria-label="切換深淺色" title="切換深淺色" onClick={toggle}>{dark ? <Sun size={22}/> : <Moon size={22}/>}</button>
        {user && <button className="rail-link" type="button" aria-label="登出" title="登出" onClick={signOut}><LogOut size={22}/></button>}
      </div>
    </aside>
    <div className="workspace">
      <header className="app-topbar">
        <Link to="/" className="wordmark"><span className="brand-dot"/><span>common<span className="wordmark-light">ground</span><small>交流廣場</small></span></Link>
        <span className="topbar-caption">一點想法，無限對話。</span>
        <div className="topbar-actions">
          {user ? <><Link to="/profile" className="account-link"><span className="avatar avatar-small">{user.nickname.slice(0,1)}</span><span>{user.nickname}</span></Link>{user.is_admin && <Link to="/admin" className="mobile-admin" aria-label="管理後台"><ShieldCheck size={19}/></Link>}<button className="mobile-control" aria-label="登出" title="登出" onClick={signOut}><LogOut size={18}/></button></> : <><Button variant="ghost" size="sm" asChild><Link to="/login">登入</Link></Button><Button size="sm" asChild><Link to="/register">加入交流<ArrowUpRight size={14}/></Link></Button></>}
          <button className="mobile-control" aria-label="切換深淺色" onClick={toggle}>{dark ? <Sun size={19}/> : <Moon size={19}/>}</button>
        </div>
      </header>
      <main className={`page-shell ${location.pathname.startsWith('/admin') ? 'page-admin' : ''}`}><Outlet/></main>
      <footer className="site-footer"><span>COMMON GROUND</span><span>保持好奇，保持真實。</span><span>© {new Date().getFullYear()}</span></footer>
    </div>
    {user && <Link to="/posts/new" className="floating-compose" aria-label="新增貼文"><SquarePen size={25}/></Link>}
  </div>;
}
