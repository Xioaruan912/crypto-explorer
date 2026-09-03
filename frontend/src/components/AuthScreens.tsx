'use client';

import { FormEvent, useState } from 'react';
import { KeyRound, Loader2, LockKeyhole, ShieldCheck, User } from 'lucide-react';
import { authService } from '@/services/authService';
import { AuthSession } from '@/types/research';

export function LoginScreen({ defaultCredentialsActive, onAuthenticated }: { defaultCredentialsActive: boolean; onAuthenticated: (session: AuthSession) => void }) {
  const [username, setUsername] = useState(defaultCredentialsActive ? 'admin' : '');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      onAuthenticated(await authService.login(username.trim(), password));
    } catch (e) {
      setError(e instanceof Error ? e.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return <div className="flex min-h-screen items-center justify-center bg-[#F8F9FC] p-6">
    <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
      <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-[#FFF7ED] text-[#F97316]"><ShieldCheck size={24} /></div>
      <h1 className="text-2xl font-bold text-gray-900">登录密码学研究图谱</h1>
      <p className="mt-2 text-sm leading-6 text-gray-500">研究数据、阅读计划和 Markdown 笔记现在都需要账号验证。</p>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <label className="block"><span className="mb-2 block text-sm font-medium text-gray-700">用户名</span><div className="relative"><User size={17} className="absolute left-3 top-3 text-gray-400" /><input autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} className="w-full rounded-lg border border-gray-200 py-2.5 pl-10 pr-3 text-sm outline-none focus:ring-2 focus:ring-[#F97316]" /></div></label>
        <label className="block"><span className="mb-2 block text-sm font-medium text-gray-700">密码</span><div className="relative"><LockKeyhole size={17} className="absolute left-3 top-3 text-gray-400" /><input autoComplete="current-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-lg border border-gray-200 py-2.5 pl-10 pr-3 text-sm outline-none focus:ring-2 focus:ring-[#F97316]" /></div></label>
        {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <button disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#F97316] py-2.5 text-sm font-semibold text-white hover:bg-orange-600 disabled:opacity-50">{loading && <Loader2 size={16} className="animate-spin" />}登录</button>
      </form>
      {defaultCredentialsActive && <div className="mt-5 rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-700">首次初始化默认账号：<strong>admin</strong>，默认密码：<strong>123456</strong>。首次登录后必须立即修改密码。</div>}
    </div>
  </div>;
}

export function ForcedPasswordChange({ session, onChanged }: { session: AuthSession; onChanged: (session: AuthSession) => void }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (newPassword !== confirm) return setError('两次输入的新密码不一致');
    if (newPassword.length < 10) return setError('新密码至少 10 位');
    setLoading(true);
    setError('');
    try {
      const updated = await authService.updateCredentials({ current_password: currentPassword, new_password: newPassword });
      onChanged({ authenticated: true, username: updated.username, must_change_password: false, csrf_token: updated.csrf_token, expires_at: updated.expires_at });
    } catch (e) {
      setError(e instanceof Error ? e.message : '修改密码失败');
    } finally {
      setLoading(false);
    }
  };

  return <div className="flex min-h-screen items-center justify-center bg-[#F8F9FC] p-6">
    <div className="w-full max-w-lg rounded-2xl border border-amber-200 bg-white p-8 shadow-sm">
      <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-amber-50 text-amber-600"><KeyRound size={24} /></div>
      <h1 className="text-2xl font-bold text-gray-900">必须修改默认密码</h1>
      <p className="mt-2 text-sm leading-6 text-gray-500">账号 <strong>{session.username}</strong> 仍在使用初始化密码。完成修改前，其他研究 API 都不会开放。</p>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <PasswordField label="当前密码" value={currentPassword} onChange={setCurrentPassword} autoComplete="current-password" />
        <PasswordField label="新密码（至少 10 位）" value={newPassword} onChange={setNewPassword} autoComplete="new-password" />
        <PasswordField label="确认新密码" value={confirm} onChange={setConfirm} autoComplete="new-password" />
        {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <button disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#F97316] py-2.5 text-sm font-semibold text-white hover:bg-orange-600 disabled:opacity-50">{loading && <Loader2 size={16} className="animate-spin" />}保存新密码并进入</button>
      </form>
    </div>
  </div>;
}

function PasswordField({ label, value, onChange, autoComplete }: { label: string; value: string; onChange: (value: string) => void; autoComplete: string }) {
  return <label className="block"><span className="mb-2 block text-sm font-medium text-gray-700">{label}</span><input type="password" autoComplete={autoComplete} value={value} onChange={(e) => onChange(e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[#F97316]" /></label>;
}
