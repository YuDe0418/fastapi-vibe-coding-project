import { Routes, Route } from 'react-router-dom';
import { SiteLayout } from '@/layouts/SiteLayout';
import { AdminLayout } from '@/layouts/AdminLayout';
import { Home } from '@/pages/Home';
import { AuthPage } from '@/pages/Auth';
import { PostDetail, PostEditor } from '@/pages/Post';
import { Profile } from '@/pages/Profile';
import { Dashboard, AdminUsers, AdminPosts, AdminSystem, AdminAudit } from '@/pages/Admin';
import { Protected, StatusPage } from '@/components/common';
export default function App() { return <Routes><Route element={<SiteLayout/>}><Route index element={<Home/>}/><Route path="login" element={<AuthPage key="login"/>}/><Route path="register" element={<AuthPage key="register" register/>}/><Route path="posts/new" element={<Protected><PostEditor/></Protected>}/><Route path="posts/:id/edit" element={<Protected><PostEditor/></Protected>}/><Route path="posts/:id" element={<PostDetail/>}/><Route path="my-posts" element={<Protected><Home mine/></Protected>}/><Route path="profile" element={<Protected><Profile/></Protected>}/><Route path="admin" element={<Protected admin><AdminLayout/></Protected>}><Route index element={<Dashboard/>}/><Route path="users" element={<AdminUsers/>}/><Route path="posts" element={<AdminPosts/>}/><Route path="system" element={<AdminSystem/>}/><Route path="audit" element={<AdminAudit/>}/></Route><Route path="401" element={<StatusPage code={401}/>}/><Route path="403" element={<StatusPage code={403}/>}/><Route path="*" element={<StatusPage code={404}/>}/></Route></Routes>; }
