import { Paper } from '../types/paper';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export interface GraphData {
  papers: Paper[];
  edges: { source: string; target: string }[];
}

export interface GraphSearchOptions {
  fromYear?: number;
  toYear?: number;
  strategy?: 'relevance' | 'foundational';
}

interface BackendAuthor {
  name: string;
}

interface BackendPaper {
  paperId: string;
  title: string;
  authors: BackendAuthor[];
  year?: number | null;
  venue?: string | null;
  abstract?: string | null;
  tldr?: string | null;
  citationCount?: number;
  referenceCount?: number;
  url?: string | null;
  doi?: string | null;
  pdf_url?: string | null;
  eprint_id?: string | null;
  role?: string;
  category?: string;
}

interface BackendNode {
  paper: BackendPaper;
  citations: string[];
}

interface BackendGraph {
  nodes: Record<string, BackendNode>;
}

// Convert Backend Category to Frontend UI Category
const mapCategory = (backendCat: string): Paper['category'] => {
  const cat = backendCat.toLowerCase();
  if (cat.includes('foundation')) return 'foundation';
  if (cat.includes('security')) return 'security';
  if (cat.includes('efficien')) return 'efficiency';
  if (cat.includes('large') || cat.includes('space')) return 'scalability';
  if (cat.includes('variant') || cat.includes('advanced')) return 'variant';
  return 'application';
};

export const paperService = {
  // Now handles searching from the real Python FastAPI backend
  searchGraph: async (query: string, options: GraphSearchOptions = {}): Promise<GraphData> => {
    const params = new URLSearchParams({ query, max_nodes: '15' });
    if (options.fromYear) params.set('from_year', String(options.fromYear));
    if (options.toYear) params.set('to_year', String(options.toYear));
    if (options.strategy) params.set('strategy', options.strategy);
    const response = await fetch(`${API_URL}/api/search?${params.toString()}`);
    if (!response.ok) {
      let detail = '搜索失败，请稍后重试';
      try {
        const body = await response.json();
        if (typeof body?.detail === 'string') detail = body.detail;
      } catch {
        // Keep the friendly fallback message.
      }
      throw new Error(detail);
    }

    const data = await response.json() as BackendGraph;
      
    const papers: Paper[] = [];
    const edges: { source: string; target: string }[] = [];
      
    Object.values(data.nodes).forEach((node) => {
      const p = node.paper;
      papers.push({
        id: p.paperId,
        titleEn: p.title,
        titleZh: p.title,
        authors: p.authors.map((a) => a.name),
        year: p.year || new Date().getFullYear(),
        venue: p.venue || 'Unknown venue',
        category: mapCategory(p.category || ''),
        citations: p.citationCount || 0,
        references: p.referenceCount || node.citations.length,
        abstractZh: p.abstract || p.tldr || '',
        abstractEn: p.abstract || '',
        eprint: p.eprint_id || undefined,
        doi: p.doi || undefined,
        pdfUrl: p.pdf_url || undefined,
        semanticScholarUrl: p.url || undefined,
        contributionsZh: p.tldr ? [p.tldr] : [],
        topicsZh: [p.category, p.role].filter((value): value is string => Boolean(value)),
      });
        
      node.citations.forEach((citedId) => {
        if (data.nodes[citedId]) {
          edges.push({ source: citedId, target: p.paperId });
        }
      });
    });

    return { papers, edges };
  }
};
