import { AccountInfo, AuthSession } from '../types/research';

let csrfToken = '';

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return typeof body?.detail === 'string' ? body.detail : '操作失败';
  } catch {
    return '操作失败';
  }
}

export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const method = (init.method || 'GET').toUpperCase();
  const headers = new Headers(init.headers || {});
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && csrfToken) {
    headers.set('x-csrf-token', csrfToken);
  }
  const response = await fetch(input, { ...init, headers, credentials: 'same-origin' });
  if (response.status === 401) {
    csrfToken = '';
    if (typeof window !== 'undefined') window.dispatchEvent(new Event('crypto-auth-expired'));
  }
  return response;
}

export const authService = {
  async session(): Promise<AuthSession> {
    const response = await fetch('/api/auth/session', { cache: 'no-store', credentials: 'same-origin' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as AuthSession;
    csrfToken = body.csrf_token || '';
    return body;
  },

  async login(username: string, password: string): Promise<AuthSession> {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ username, password }),
      credentials: 'same-origin',
    });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as AuthSession;
    csrfToken = body.csrf_token || '';
    return body;
  },

  async logout(): Promise<void> {
    const response = await authFetch('/api/auth/logout', { method: 'POST' });
    if (!response.ok) throw new Error(await parseError(response));
    csrfToken = '';
  },

  async account(): Promise<AccountInfo> {
    const response = await authFetch('/api/auth/account', { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    return response.json();
  },

  async updateCredentials(input: { current_password: string; username?: string; new_password?: string }): Promise<AccountInfo & { csrf_token: string; expires_at: string }> {
    const response = await authFetch('/api/auth/credentials', {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as AccountInfo & { csrf_token: string; expires_at: string };
    csrfToken = body.csrf_token || '';
    return body;
  },

  async downloadBackup(): Promise<void> {
    const response = await authFetch('/api/backup/export', { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const blob = await response.blob();
    const disposition = response.headers.get('content-disposition') || '';
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const fileName = match?.[1] || `crypto-explorer-backup-${new Date().toISOString().slice(0, 10)}.json`;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = fileName;
    anchor.click();
    URL.revokeObjectURL(url);
  },

  async importBackup(file: File): Promise<void> {
    if (file.size > 5 * 1024 * 1024) throw new Error('备份文件不能超过 5 MB');
    let backup: unknown;
    try {
      backup = JSON.parse(await file.text());
    } catch {
      throw new Error('备份文件不是有效 JSON');
    }
    const response = await authFetch('/api/backup/import', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ backup }),
    });
    if (!response.ok) throw new Error(await parseError(response));
  },
};
