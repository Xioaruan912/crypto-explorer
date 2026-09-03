import { Paper } from './paper';

export type ResearchView = 'graph' | 'timeline' | 'citations' | 'reading' | 'papers' | 'authors' | 'venues';
export type ReadingStatus = 'to_read' | 'reading' | 'done';
export type ReadingTaskStatus = 'todo' | 'doing' | 'done';
export type ReadingTaskType = 'read' | 'notes' | 'review' | 'reproduce' | 'custom';
export type WorkspaceSection = 'help' | 'dashboard' | 'history' | 'favorites' | 'profile' | 'notes';

export interface ReadingListItem {
  paper: Paper;
  status: ReadingStatus;
  priority: 1 | 2 | 3;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface ReadingTask {
  id: number;
  paper: Paper;
  task_type: ReadingTaskType;
  task_text: string;
  scheduled_date: string;
  status: ReadingTaskStatus;
  created_at: string;
  updated_at: string;
}

export interface FavoriteItem {
  paper: Paper;
  created_at: string;
}

export interface SearchHistoryItem {
  id: number;
  query: string;
  result_count: number;
  seed_title: string;
  search_type?: 'graph' | 'papers' | 'authors' | 'venues';
  created_at: string;
}

export interface UserProfile {
  id: number;
  display_name: string;
  role: string;
  institution: string;
  research_interests: string;
  updated_at: string;
}

export interface DashboardData {
  reading_count: number;
  favorite_count: number;
  history_count: number;
  note_count: number;
  reading_statuses: Partial<Record<ReadingStatus, number>>;
  recent_searches: SearchHistoryItem[];
}

export interface NoteItem {
  paper: Paper;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface ResearchTimeRange {
  fromYear?: number;
  toYear?: number;
  strategy: 'relevance' | 'foundational';
}
