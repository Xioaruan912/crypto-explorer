import { Paper } from '../types/paper';
import { authFetch } from './authService';
import {
  DashboardData,
  FavoriteItem,
  NoteItem,
  ReadingListItem,
  ReadingStatus,
  ReadingTask,
  ReadingTaskStatus,
  ReadingTaskType,
  SearchHistoryItem,
  UserProfile,
} from '../types/research';

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return typeof body?.detail === 'string' ? body.detail : '操作失败';
  } catch {
    return '操作失败';
  }
}

export const researchService = {
  async listReading(): Promise<ReadingListItem[]> {
    const response = await authFetch('/api/reading-list', { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as { items: ReadingListItem[] };
    return body.items;
  },

  async addReading(paper: Paper): Promise<ReadingListItem> {
    const response = await authFetch('/api/reading-list', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ paper, status: 'to_read', priority: 2, note: '' }),
    });
    if (!response.ok) throw new Error(await parseError(response));
    return response.json();
  },

  async updateReading(
    paperId: string,
    patch: Partial<{ status: ReadingStatus; priority: 1 | 2 | 3; note: string }>,
  ): Promise<ReadingListItem> {
    const response = await authFetch(`/api/reading-list/${encodeURIComponent(paperId)}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(patch),
    });
    if (!response.ok) throw new Error(await parseError(response));
    return response.json();
  },

  async removeReading(paperId: string): Promise<void> {
    const response = await authFetch(`/api/reading-list/${encodeURIComponent(paperId)}`, { method: 'DELETE' });
    if (!response.ok) throw new Error(await parseError(response));
  },

  async listReadingTasks(fromDate: string, toDate: string): Promise<ReadingTask[]> {
    const params = new URLSearchParams({ from_date: fromDate, to_date: toDate });
    const response = await authFetch(`/api/reading-tasks?${params.toString()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as { items: ReadingTask[] };
    return body.items;
  },

  async createReadingTask(input: {
    paperId: string;
    scheduledDate: string;
    taskType: ReadingTaskType;
    taskText: string;
  }): Promise<ReadingTask> {
    const response = await authFetch('/api/reading-tasks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        paper_id: input.paperId,
        scheduled_date: input.scheduledDate,
        task_type: input.taskType,
        task_text: input.taskText,
        status: 'todo',
      }),
    });
    if (!response.ok) throw new Error(await parseError(response));
    return response.json();
  },

  async updateReadingTask(
    taskId: number,
    patch: Partial<{
      scheduled_date: string;
      task_type: ReadingTaskType;
      task_text: string;
      status: ReadingTaskStatus;
    }>,
  ): Promise<ReadingTask> {
    const response = await authFetch(`/api/reading-tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(patch),
    });
    if (!response.ok) throw new Error(await parseError(response));
    return response.json();
  },

  async removeReadingTask(taskId: number): Promise<void> {
    const response = await authFetch(`/api/reading-tasks/${taskId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error(await parseError(response));
  },

  async listFavorites(): Promise<FavoriteItem[]> {
    const response = await authFetch('/api/favorites', { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as { items: FavoriteItem[] };
    return body.items;
  },

  async addFavorite(paper: Paper): Promise<FavoriteItem> {
    const response = await authFetch('/api/favorites', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ paper }),
    });
    if (!response.ok) throw new Error(await parseError(response));
    return response.json();
  },

  async removeFavorite(paperId: string): Promise<void> {
    const response = await authFetch(`/api/favorites/${encodeURIComponent(paperId)}`, { method: 'DELETE' });
    if (!response.ok) throw new Error(await parseError(response));
  },

  async listHistory(): Promise<SearchHistoryItem[]> {
    const response = await authFetch('/api/history', { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as { items: SearchHistoryItem[] };
    return body.items;
  },

  async removeHistory(id: number): Promise<void> {
    const response = await authFetch(`/api/history/${id}`, { method: 'DELETE' });
    if (!response.ok) throw new Error(await parseError(response));
  },

  async clearHistory(): Promise<void> {
    const response = await authFetch('/api/history', { method: 'DELETE' });
    if (!response.ok) throw new Error(await parseError(response));
  },

  async getDashboard(): Promise<DashboardData> {
    const response = await authFetch('/api/dashboard', { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    return response.json();
  },

  async getProfile(): Promise<UserProfile> {
    const response = await authFetch('/api/profile', { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    return response.json();
  },

  async updateProfile(patch: Partial<Omit<UserProfile, 'id' | 'updated_at'>>): Promise<UserProfile> {
    const response = await authFetch('/api/profile', {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(patch),
    });
    if (!response.ok) throw new Error(await parseError(response));
    return response.json();
  },

  async listNotes(): Promise<NoteItem[]> {
    const response = await authFetch('/api/notes', { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as { items: NoteItem[] };
    return body.items;
  },

  async getNote(paperId: string): Promise<NoteItem | null> {
    const response = await authFetch(`/api/notes/${encodeURIComponent(paperId)}`, { cache: 'no-store' });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(await parseError(response));
    return response.json();
  },

  async saveNote(paper: Paper, title: string, content: string): Promise<NoteItem> {
    const response = await authFetch(`/api/notes/${encodeURIComponent(paper.id)}`, {
      method: 'PUT',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ paper, title, content }),
    });
    if (!response.ok) throw new Error(await parseError(response));
    return response.json();
  },

  async removeNote(paperId: string): Promise<void> {
    const response = await authFetch(`/api/notes/${encodeURIComponent(paperId)}`, { method: 'DELETE' });
    if (!response.ok) throw new Error(await parseError(response));
  },
};
