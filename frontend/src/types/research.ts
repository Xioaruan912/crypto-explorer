import { Paper } from './paper';

export type ResearchView = 'graph' | 'timeline' | 'citations' | 'reading' | 'papers' | 'authors' | 'venues' | 'draw';
export type StudyMode = 'related' | 'origin' | 'learning';
export type SearchLanguageMode = 'academic_en' | 'original';
export type ReadingStatus = 'to_read' | 'reading' | 'done';
export type ReadingTaskStatus = 'todo' | 'doing' | 'done';
export type ReadingTaskType = 'read' | 'notes' | 'review' | 'reproduce' | 'custom';
export type WorkspaceSection = 'help' | 'dashboard' | 'history' | 'favorites' | 'profile' | 'notes' | 'terms' | 'account';

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
  effective_query?: string;
  query_language?: 'zh' | 'en' | 'mixed' | 'unknown';
  language_mode?: SearchLanguageMode;
  normalized_terms_json?: string;
  result_count: number;
  seed_title: string;
  search_type?: 'graph' | 'papers' | 'authors' | 'venues';
  created_at: string;
}

export interface QueryInfo {
  originalQuery: string;
  detectedLanguage: 'zh' | 'en' | 'mixed';
  requestedMode: SearchLanguageMode;
  effectiveQuery: string;
  normalizedTerms: string[];
  historicalTerms: string[];
  translated: boolean;
  glossaryMatch?: string | null;
  confidence: 'direct' | 'high' | 'medium' | 'low';
  confidenceScore?: number | null;
  notice: string;
  resolutionStatus?: 'direct' | 'local' | 'bootstrap' | 'dynamic' | 'unresolved';
  sources?: string[];
  termMappingId?: number | null;
  userConfirmed?: boolean;
  aliases?: string[];
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

export interface AuthSession {
  authenticated: boolean;
  default_credentials_active?: boolean;
  username?: string;
  must_change_password?: boolean;
  csrf_token?: string;
  expires_at?: string;
}

export interface AccountInfo {
  username: string;
  must_change_password: boolean;
  updated_at: string;
  active_sessions: number;
}

export interface GenealogyPaper {
  paper: Paper;
  distance: number;
  anchorCoverage: number;
  reason: string;
}

export interface GenealogyStage {
  stage: '开山论文' | '早期奠基' | '关键演进' | '现代代表';
  papers: GenealogyPaper[];
}

export interface GenealogyBranch {
  name: string;
  papers: GenealogyPaper[];
}

export interface GenealogyData {
  query: string;
  queryInfo?: QueryInfo;
  historicalQuery?: string | null;
  anchors: GenealogyPaper[];
  origin: GenealogyPaper | null;
  background: GenealogyPaper[];
  prerequisites: GenealogyPaper[];
  classics: GenealogyPaper[];
  learningPath: GenealogyStage[];
  branches: GenealogyBranch[];
  pool: GenealogyPaper[];
  poolCount: number;
}

export interface TermMapping {
  id: number;
  source_term: string;
  source_language: string;
  canonical_term: string;
  canonical_language: string;
  aliases: string[];
  related_terms: string[];
  historical_terms: string[];
  sources: string[];
  confidence: number;
  wikidata_id: string;
  nist_term: string;
  cso_topic: string;
  openalex_hits: number;
  user_confirmed: boolean;
  created_at: string;
  updated_at: string;
  last_verified_at: string;
}

export interface DrawHistoryItem {
  id: number;
  query: string;
  paper: Paper;
  reason: string;
  created_at: string;
}

export interface DrawResponse {
  selected: GenealogyPaper;
  reel: GenealogyPaper[];
  poolCount: number;
  historyItem: DrawHistoryItem;
  origin: GenealogyPaper | null;
  queryInfo: QueryInfo;
}
