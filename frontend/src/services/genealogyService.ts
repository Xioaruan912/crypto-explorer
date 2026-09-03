import { Paper } from '../types/paper';
import { DrawHistoryItem, DrawResponse, GenealogyData, GenealogyPaper, QueryInfo, ResearchTimeRange, SearchLanguageMode } from '../types/research';
import { authFetch } from './authService';

interface BackendAuthorRef { name: string }
interface BackendWork {
  paperId: string;
  title: string;
  authors?: BackendAuthorRef[];
  year?: number | null;
  venue?: string | null;
  abstract?: string | null;
  citationCount?: number;
  referenceCount?: number;
  url?: string | null;
  externalIds?: { DOI?: string | null };
  openAccessPdf?: { url?: string | null } | null;
  primaryTopic?: string | null;
}

interface BackendGenealogyPaper {
  paper: BackendWork;
  distance: number;
  anchorCoverage: number;
  reason: string;
}

interface BackendGenealogyData {
  query: string;
  queryInfo?: QueryInfo;
  historicalQuery?: string | null;
  anchors: BackendGenealogyPaper[];
  origin: BackendGenealogyPaper | null;
  prerequisites: BackendGenealogyPaper[];
  classics: BackendGenealogyPaper[];
  learningPath: { stage: GenealogyData['learningPath'][number]['stage']; papers: BackendGenealogyPaper[] }[];
  pool: BackendGenealogyPaper[];
  poolCount: number;
}

interface BackendDrawHistoryItem {
  id: number;
  query: string;
  paper: BackendWork;
  reason: string;
  created_at: string;
}

interface BackendDrawResponse {
  selected: BackendGenealogyPaper;
  reel: BackendGenealogyPaper[];
  poolCount: number;
  historyItem: BackendDrawHistoryItem;
  origin: BackendGenealogyPaper | null;
  queryInfo: QueryInfo;
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return typeof body?.detail === 'string' ? body.detail : '加载基础论文失败';
  } catch {
    return '加载基础论文失败';
  }
}

function mapWork(work: BackendWork): Paper {
  return {
    id: work.paperId,
    titleEn: work.title,
    titleZh: work.title,
    authors: (work.authors || []).map((author) => author.name),
    year: work.year || new Date().getFullYear(),
    venue: work.venue || 'Unknown venue',
    category: 'foundation',
    citations: work.citationCount || 0,
    references: work.referenceCount || 0,
    abstractZh: work.abstract || '',
    abstractEn: work.abstract || '',
    doi: work.externalIds?.DOI || undefined,
    pdfUrl: work.openAccessPdf?.url || undefined,
    semanticScholarUrl: work.url || undefined,
    topicsZh: [work.primaryTopic || '', '基础论文'].filter(Boolean),
  };
}

function mapItem(item: BackendGenealogyPaper): GenealogyPaper {
  return { ...item, paper: mapWork(item.paper) };
}

function queryString(query: string, range?: Partial<ResearchTimeRange>, poolSize = 24, languageMode: SearchLanguageMode = 'academic_en') {
  const params = new URLSearchParams({ query, pool_size: String(poolSize) });
  if (range?.fromYear) params.set('from_year', String(range.fromYear));
  if (range?.toYear) params.set('to_year', String(range.toYear));
  params.set('language_mode', languageMode);
  return params.toString();
}

export const genealogyService = {
  async getGenealogy(query: string, range?: Partial<ResearchTimeRange>, languageMode: SearchLanguageMode = 'academic_en'): Promise<GenealogyData> {
    const response = await authFetch(`/api/genealogy?${queryString(query, range, 24, languageMode)}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as BackendGenealogyData;
    return {
      ...body,
      anchors: body.anchors.map(mapItem),
      origin: body.origin ? mapItem(body.origin) : null,
      prerequisites: body.prerequisites.map(mapItem),
      classics: body.classics.map(mapItem),
      learningPath: body.learningPath.map((stage) => ({ ...stage, papers: stage.papers.map(mapItem) })),
      pool: body.pool.map(mapItem),
    };
  },

  async draw(input: { query: string; fromYear?: number; toYear?: number; foundationalOnly: boolean; languageMode: SearchLanguageMode }): Promise<DrawResponse> {
    const response = await authFetch('/api/paper-draw', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query: input.query,
        from_year: input.fromYear,
        to_year: input.toYear,
        foundational_only: input.foundationalOnly,
        language_mode: input.languageMode,
      }),
    });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as BackendDrawResponse;
    return {
      selected: mapItem(body.selected),
      reel: body.reel.map(mapItem),
      poolCount: body.poolCount,
      historyItem: { ...body.historyItem, paper: mapWork(body.historyItem.paper) },
      origin: body.origin ? mapItem(body.origin) : null,
      queryInfo: body.queryInfo,
    };
  },

  async history(limit = 20): Promise<DrawHistoryItem[]> {
    const response = await authFetch(`/api/paper-draw/history?limit=${limit}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as { items: BackendDrawHistoryItem[] };
    return body.items.map((item) => ({ ...item, paper: mapWork(item.paper) }));
  },

  async clearHistory(): Promise<void> {
    const response = await authFetch('/api/paper-draw/history', { method: 'DELETE' });
    if (!response.ok) throw new Error(await parseError(response));
  },
};
