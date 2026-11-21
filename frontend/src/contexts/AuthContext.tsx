import { createContext, useContext, useEffect, useState } from 'react';
import type { User } from '@/types';
import { api, json } from '@/services/api';
type Auth = { user: User | null; loading: boolean; setUser: (u: User | null) => void; login: (username: string, password: string) => Promise<User>; logout: () => Promise<void> };
const AuthContext = createContext<Auth | null>(null);
export function AuthProvider({ children }: { children: React.ReactNode }) {
 const [user, setUser] = useState<User | null>(null); const [loading, setLoading] = useState(true);
 useEffect(() => { api<User>('/users/me').then(setUser).catch(() => setUser(null)).finally(() => setLoading(false)); const expired = () => setUser(null); window.addEventListener('session-expired', expired); return () => window.removeEventListener('session-expired', expired); }, []);
 const login = async (username: string, password: string) => { const u = await api<User>('/users/login', json('POST', { username, password })); setUser(u); return u; };
 const logout = async () => { await api('/users/logout', json('POST')); setUser(null); };
 return <AuthContext.Provider value={{ user, loading, setUser, login, logout }}>{children}</AuthContext.Provider>;
}
export function useAuth() { const ctx = useContext(AuthContext); if (!ctx) throw new Error('AuthProvider missing'); return ctx; }
