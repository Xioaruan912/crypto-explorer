import { Paper } from '../types/paper';
import {
  DiscoveryAuthor,
  DiscoveryAuthorDetail,
  DiscoveryVenue,
  DiscoveryVenueDetail,
  EntitySort,
  PaperSearchParams,
} from '../types/discovery';

interface BackendAuthorRef {
  authorId?: string | null;
  name: string;
}

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
  isOpenAccess?: boolean;
  publicationDate?: string | null;
  workType?: string | null;
  primaryTopic?: string | null;
}

interface BackendAuthor extends Omit<DiscoveryAuthor, 'id'> {
  id?: string | null;
  topWorks?: BackendWork[];
}

interface BackendVenue extends Omit<DiscoveryVenue, 'id'> {
  id?: string | null;
  topWorks?: BackendWork[];
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return typeof body?.detail === 'string' ? body.detail : '检索失败';
  } catch {
    return '检索失败';
  }
}

function inferCategory(topic = ''): Paper['category'] {
  const value = topic.toLowerCase();
  if (value.includes('security') || value.includes('attack') || value.includes('proof')) return 'security';
  if (value.includes('efficien') || value.includes('performance') || value.includes('fast')) return 'efficiency';
  if (value.includes('scale') || value.includes('distributed') || value.includes('network')) return 'scalability';
  if (value.includes('foundation') || value.includes('theory')) return 'foundation';
  if (value.includes('variant') || value.includes('extension')) return 'variant';
  return 'application';
}

function mapWork(work: BackendWork): Paper {
  const topic = work.primaryTopic || '';
  const pdfUrl = work.openAccessPdf?.url || undefined;
  return {
    id: work.paperId,
    titleEn: work.title,
    titleZh: work.title,
    authors: (work.authors || []).map((author) => author.name),
    year: work.year || new Date().getFullYear(),
    venue: work.venue || 'Unknown venue',
    category: inferCategory(topic),
    citations: work.citationCount || 0,
    references: work.referenceCount || 0,
    abstractZh: work.abstract || '',
    abstractEn: work.abstract || '',
    doi: work.externalIds?.DOI || undefined,
    pdfUrl,
    semanticScholarUrl: work.url || undefined,
    topicsZh: [topic, work.workType || '', work.isOpenAccess ? 'Open Access' : ''].filter(Boolean),
  };
}

function paramsToQuery(params: Record<string, string | number | boolean | undefined>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== false) query.set(key, String(value));
  });
  return query.toString();
}

export const discoveryService = {
  async searchPapers(params: PaperSearchParams): Promise<Paper[]> {
    const response = await fetch(`/api/discovery/papers?${paramsToQuery({
      query: params.query,
      from_year: params.fromYear,
      to_year: params.toYear,
      author: params.author,
      venue: params.venue,
      sort: params.sort || 'relevance',
      open_access: params.openAccess,
      limit: 30,
    })}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as { items: BackendWork[] };
    return body.items.map(mapWork);
  },

  async searchAuthors(query: string, sort: EntitySort = 'relevance'): Promise<DiscoveryAuthor[]> {
    const response = await fetch(`/api/discovery/authors?${paramsToQuery({ query, sort, limit: 25 })}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as { items: BackendAuthor[] };
    return body.items
      .filter((item): item is BackendAuthor & { id: string } => Boolean(item.id))
      .map((item) => ({ ...item, id: item.id }));
  },

  async getAuthor(id: string): Promise<DiscoveryAuthorDetail> {
    const response = await fetch(`/api/discovery/authors/${encodeURIComponent(id)}?works_limit=15`, { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as BackendAuthor & { id: string; topWorks?: BackendWork[] };
    return { ...body, topWorks: (body.topWorks || []).map(mapWork) };
  },

  async searchVenues(query: string, sort: EntitySort = 'relevance'): Promise<DiscoveryVenue[]> {
    const response = await fetch(`/api/discovery/venues?${paramsToQuery({ query, sort, limit: 25 })}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as { items: BackendVenue[] };
    return body.items
      .filter((item): item is BackendVenue & { id: string } => Boolean(item.id))
      .map((item) => ({ ...item, id: item.id }));
  },

  async getVenue(id: string): Promise<DiscoveryVenueDetail> {
    const response = await fetch(`/api/discovery/venues/${encodeURIComponent(id)}?works_limit=15`, { cache: 'no-store' });
    if (!response.ok) throw new Error(await parseError(response));
    const body = await response.json() as BackendVenue & { id: string; topWorks?: BackendWork[] };
    return { ...body, topWorks: (body.topWorks || []).map(mapWork) };
  },
};
