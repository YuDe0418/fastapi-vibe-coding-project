export type User = { id: number; username: string; nickname: string; email: string; phone: string; address: string; is_admin: boolean; must_change_password: boolean; created_at: string };
export type Reply = { id: number; post_id: number; author_id: number; author_name: string; content: string; created_at: string };
export type LikeState = { like_count: number; real_like_count: number; demo_like_count: number; liked_by_me: boolean };
export type Post = LikeState & { is_pinned?: boolean; id: number; author_id: number; author_name: string; title: string; content: string; remarks: string; created_at: string; expires_at: string; is_expired: boolean; reply_count: number; replies?: Reply[] };
export type Page<T> = { items: T[]; total: number; page: number; page_size: number };
export type AuditLog = { id: number; actor_name: string; action: string; target: string; created_at: string };
export type Stats = { users: number; posts: number; replies: number; active_posts: number; recent_users: User[]; recent_posts: Post[]; activity: { date: string; posts: number; replies: number }[] };
