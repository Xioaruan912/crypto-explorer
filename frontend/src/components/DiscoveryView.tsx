'use client';

import React, { FormEvent, useState } from 'react';
import {
  Bookmark,
  BookOpenCheck,
  Building2,
  CalendarRange,
  ExternalLink,
  FileText,
  Filter,
  Loader2,
  Search,
  Users,
} from 'lucide-react';
import { discoveryService } from '../services/discoveryService';
import {
  DiscoveryAuthor,
  DiscoveryAuthorDetail,
  DiscoveryMode,
  DiscoveryVenue,
  DiscoveryVenueDetail,
  EntitySort,
  PaperSort,
} from '../types/discovery';
import { Paper } from '../types/paper';
import { safeExternalUrl } from '../utils/url';
import { QueryInfo, SearchLanguageMode } from '../types/research';
import { QueryLanguageNotice, SearchLanguageToggle } from './SearchLanguageControl';

interface DiscoveryViewProps {
  mode: DiscoveryMode;
  favoriteIds: Set<string>;
  readingIds: Set<string>;
  searchLanguageMode: SearchLanguageMode;
  onSearchLanguageModeChange: (mode: SearchLanguageMode) => void;
  onSelectPaper: (paper: Paper) => void;
  onToggleFavorite: (paper: Paper) => void;
  onAddReading: (paper: Paper) => void;
}

const MODE_META = {
  papers: {
    title: '论文检索',
    description: '按关键词、作者、会议、年份与开放获取状态检索论文。',
    placeholder: '输入论文标题、主题、技术关键词，例如 lattice signatures',
    icon: FileText,
  },
  authors: {
    title: '作者检索',
    description: '查找研究者、机构信息、学术影响力与代表论文。',
    placeholder: '输入作者姓名，例如 Dan Boneh',
    icon: Users,
  },
  venues: {
    title: '会议 / 期刊检索',
    description: '查找会议、期刊与出版来源，并查看其中高影响力论文。',
    placeholder: '输入会议或期刊名称，例如 CRYPTO / IEEE S&P',
    icon: Building2,
  },
} as const;

export default function DiscoveryView({
  mode,
  favoriteIds,
  readingIds,
  searchLanguageMode,
  onSearchLanguageModeChange,
  onSelectPaper,
  onToggleFavorite,
  onAddReading,
}: DiscoveryViewProps) {
  const meta = MODE_META[mode];
  const Icon = meta.icon;
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queryInfo, setQueryInfo] = useState<QueryInfo | null>(null);

  const [papers, setPapers] = useState<Paper[]>([]);
  const [authors, setAuthors] = useState<DiscoveryAuthor[]>([]);
  const [venues, setVenues] = useState<DiscoveryVenue[]>([]);
  const [authorDetail, setAuthorDetail] = useState<DiscoveryAuthorDetail | null>(null);
  const [venueDetail, setVenueDetail] = useState<DiscoveryVenueDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [fromYear, setFromYear] = useState('');
  const [toYear, setToYear] = useState('');
  const [paperAuthor, setPaperAuthor] = useState('');
  const [paperVenue, setPaperVenue] = useState('');
  const [paperSort, setPaperSort] = useState<PaperSort>('relevance');
  const [openAccess, setOpenAccess] = useState(false);
  const [entitySort, setEntitySort] = useState<EntitySort>('relevance');

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const value = query.trim();
    if (value.length < 2) return;
    setLoading(true);
    setError(null);
    setAuthorDetail(null);
    setVenueDetail(null);
    try {
      if (mode === 'papers') {
        const result = await discoveryService.searchPapers({
          query: value,
          fromYear: fromYear ? Number(fromYear) : undefined,
          toYear: toYear ? Number(toYear) : undefined,
          author: paperAuthor.trim() || undefined,
          venue: paperVenue.trim() || undefined,
          sort: paperSort,
          openAccess,
        }, searchLanguageMode);
        setPapers(result.items);
        setQueryInfo(result.queryInfo || null);
      } else if (mode === 'authors') {
        setQueryInfo(null);
        setAuthors(await discoveryService.searchAuthors(value, entitySort));
      } else {
        setQueryInfo(null);
        setVenues(await discoveryService.searchVenues(value, entitySort));
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '检索失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const loadAuthor = async (author: DiscoveryAuthor) => {
    setDetailLoading(true);
    setError(null);
    try {
      setAuthorDetail(await discoveryService.getAuthor(author.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '作者详情加载失败');
    } finally {
      setDetailLoading(false);
    }
  };

  const loadVenue = async (venue: DiscoveryVenue) => {
    setDetailLoading(true);
    setError(null);
    try {
      setVenueDetail(await discoveryService.getVenue(venue.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '会议 / 期刊详情加载失败');
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#FFF7ED] text-[#F97316]">
          <Icon size={22} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{meta.title}</h1>
          <p className="mt-1 text-sm text-gray-500">{meta.description}</p>
        </div>
      </div>

      <form onSubmit={submit} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={meta.placeholder}
              className="w-full rounded-lg border border-gray-200 bg-gray-50 py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-[#F97316] focus:ring-2 focus:ring-[#F97316]/15"
            />
          </div>
          <button
            type="submit"
            disabled={loading || query.trim().length < 2}
            className="flex min-w-24 items-center justify-center gap-2 rounded-lg bg-[#F97316] px-4 py-2 text-sm font-medium text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            检索
          </button>
          {mode === 'papers' && <SearchLanguageToggle mode={searchLanguageMode} onChange={(next) => { onSearchLanguageModeChange(next); setQueryInfo(null); }} compact />}
        </div>

        {mode === 'papers' && <QueryLanguageNotice info={queryInfo} className="mt-3" />}

        {mode === 'papers' ? (
          <div className="mt-4 grid grid-cols-2 gap-3 border-t border-gray-100 pt-4 lg:grid-cols-6">
            <FilterField label="起始年份" icon={<CalendarRange size={14} />}>
              <input type="number" min="1900" max="2100" value={fromYear} onChange={(e) => setFromYear(e.target.value)} placeholder="例如 2020" className="filter-input" />
            </FilterField>
            <FilterField label="结束年份" icon={<CalendarRange size={14} />}>
              <input type="number" min="1900" max="2100" value={toYear} onChange={(e) => setToYear(e.target.value)} placeholder="例如 2026" className="filter-input" />
            </FilterField>
            <FilterField label="作者" icon={<Users size={14} />}>
              <input value={paperAuthor} onChange={(e) => setPaperAuthor(e.target.value)} placeholder="作者名" className="filter-input" />
            </FilterField>
            <FilterField label="会议 / 期刊" icon={<Building2 size={14} />}>
              <input value={paperVenue} onChange={(e) => setPaperVenue(e.target.value)} placeholder="CRYPTO" className="filter-input" />
            </FilterField>
            <FilterField label="排序" icon={<Filter size={14} />}>
              <select value={paperSort} onChange={(e) => setPaperSort(e.target.value as PaperSort)} className="filter-input">
                <option value="relevance">相关度</option>
                <option value="citations">被引次数</option>
                <option value="newest">最新发表</option>
              </select>
            </FilterField>
            <label className="flex items-end pb-1 text-sm text-gray-600">
              <span className="flex w-full items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5">
                <input type="checkbox" checked={openAccess} onChange={(e) => setOpenAccess(e.target.checked)} />
                仅开放获取
              </span>
            </label>
          </div>
        ) : (
          <div className="mt-4 flex items-center justify-end gap-2 border-t border-gray-100 pt-4 text-sm text-gray-500">
            <Filter size={15} /> 排序
            <select value={entitySort} onChange={(e) => setEntitySort(e.target.value as EntitySort)} className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-700 outline-none">
              <option value="relevance">相关度</option>
              <option value="citations">总被引次数</option>
              <option value="works">论文数量</option>
            </select>
          </div>
        )}
      </form>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {mode === 'papers' && (
        <PaperResults
          papers={papers}
          loading={loading}
          searched={Boolean(query.trim())}
          favoriteIds={favoriteIds}
          readingIds={readingIds}
          onSelectPaper={onSelectPaper}
          onToggleFavorite={onToggleFavorite}
          onAddReading={onAddReading}
        />
      )}

      {mode === 'authors' && (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <EntityList
            emptyLabel="没有找到匹配的作者"
            loading={loading}
            items={authors}
            render={(author) => (
              <button key={author.id} type="button" onClick={() => loadAuthor(author)} className="w-full overflow-hidden rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-[#FDBA74] hover:shadow-md">
                <div className="truncate font-semibold text-gray-900" title={author.name}>{author.name}</div>
                <div className="mt-1 truncate text-sm text-gray-500" title={author.institutions.join(' · ')}>{author.institutions.join(' · ') || '机构信息暂无'}</div>
                <div className="mt-3 flex gap-4 text-xs text-gray-500"><span>{author.worksCount.toLocaleString()} 篇论文</span><span>{author.citedByCount.toLocaleString()} 次被引</span></div>
              </button>
            )}
          />
          <AuthorDetailPanel
            detail={authorDetail}
            loading={detailLoading}
            favoriteIds={favoriteIds}
            readingIds={readingIds}
            onSelectPaper={onSelectPaper}
            onToggleFavorite={onToggleFavorite}
            onAddReading={onAddReading}
          />
        </div>
      )}

      {mode === 'venues' && (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <EntityList
            emptyLabel="没有找到匹配的会议或期刊"
            loading={loading}
            items={venues}
            render={(venue) => (
              <button key={venue.id} type="button" onClick={() => loadVenue(venue)} className="w-full overflow-hidden rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-[#FDBA74] hover:shadow-md">
                <div className="flex min-w-0 items-start justify-between gap-3"><div className="min-w-0 truncate font-semibold text-gray-900" title={venue.name}>{venue.name}</div><span className="shrink-0 rounded-full bg-gray-100 px-2 py-1 text-[11px] text-gray-500">{venue.type || 'source'}</span></div>
                <div className="mt-1 truncate text-sm text-gray-500" title={venue.hostOrganization || venue.issn || ''}>{venue.hostOrganization || venue.issn || '出版机构信息暂无'}</div>
                <div className="mt-3 flex gap-4 text-xs text-gray-500"><span>{venue.worksCount.toLocaleString()} 篇论文</span><span>{venue.citedByCount.toLocaleString()} 次被引</span>{venue.isOpenAccess && <span className="text-emerald-600">Open Access</span>}</div>
              </button>
            )}
          />
          <VenueDetailPanel
            detail={venueDetail}
            loading={detailLoading}
            favoriteIds={favoriteIds}
            readingIds={readingIds}
            onSelectPaper={onSelectPaper}
            onToggleFavorite={onToggleFavorite}
            onAddReading={onAddReading}
          />
        </div>
      )}

      <style jsx global>{`
        .filter-input { width: 100%; border-radius: .5rem; border: 1px solid #e5e7eb; background: #f9fafb; padding: .55rem .65rem; font-size: .8rem; color: #374151; outline: none; }
        .filter-input:focus { border-color: #F97316; box-shadow: 0 0 0 2px rgba(249,115,22,.12); }
      `}</style>
    </div>
  );
}

function FilterField({ label, icon, children }: { label: string; icon: React.ReactNode; children: React.ReactNode }) {
  return <label className="block"><span className="mb-1.5 flex items-center gap-1 text-xs font-medium text-gray-500">{icon}{label}</span>{children}</label>;
}

function EntityList<T>({ items, render, loading, emptyLabel }: { items: T[]; render: (item: T) => React.ReactNode; loading: boolean; emptyLabel: string }) {
  if (loading) return <LoadingCard />;
  if (!items.length) return <EmptyCard label={emptyLabel} />;
  return <div className="space-y-3">{items.map(render)}</div>;
}

function PaperResults({
  papers,
  loading,
  searched,
  favoriteIds,
  readingIds,
  onSelectPaper,
  onToggleFavorite,
  onAddReading,
}: {
  papers: Paper[];
  loading: boolean;
  searched: boolean;
  favoriteIds: Set<string>;
  readingIds: Set<string>;
  onSelectPaper: (paper: Paper) => void;
  onToggleFavorite: (paper: Paper) => void;
  onAddReading: (paper: Paper) => void;
}) {
  if (loading) return <LoadingCard />;
  if (!papers.length) return <EmptyCard label={searched ? '没有找到符合当前条件的论文' : '输入关键词并设置筛选条件后开始检索'} />;
  return (
    <div className="space-y-3">
      <div className="text-sm text-gray-500">找到 {papers.length} 条结果</div>
      {papers.map((paper) => (
        <PaperCard
          key={paper.id}
          paper={paper}
          isFavorite={favoriteIds.has(paper.id)}
          inReading={readingIds.has(paper.id)}
          onSelect={() => onSelectPaper(paper)}
          onToggleFavorite={() => onToggleFavorite(paper)}
          onAddReading={() => onAddReading(paper)}
        />
      ))}
    </div>
  );
}

function PaperCard({ paper, isFavorite, inReading, onSelect, onToggleFavorite, onAddReading }: { paper: Paper; isFavorite: boolean; inReading: boolean; onSelect: () => void; onToggleFavorite: () => void; onAddReading: () => void }) {
  const sourceUrl = safeExternalUrl(paper.semanticScholarUrl);
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:border-gray-300 hover:shadow-md">
      <div className="flex gap-4">
        <button type="button" onClick={onSelect} className="min-w-0 flex-1 text-left">
          <div className="line-clamp-2 break-words font-semibold leading-6 text-gray-900 hover:text-[#F97316]">{paper.titleEn}</div>
          <div className="mt-1 truncate text-sm text-gray-500">{paper.authors.join(', ') || '作者未知'}</div>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
            <span>{paper.year}</span><span className="max-w-[360px] truncate" title={paper.venue}>{paper.venue}</span><span>{paper.citations || 0} 次被引</span><span>{paper.references || 0} 篇参考文献</span>
            {paper.pdfUrl && <span className="text-emerald-600">Open Access</span>}
          </div>
        </button>
        <div className="flex shrink-0 items-start gap-2">
          <button type="button" onClick={onToggleFavorite} title={isFavorite ? '取消收藏' : '收藏'} className={`rounded-lg border p-2 transition ${isFavorite ? 'border-[#FDBA74] bg-[#FFF7ED] text-[#F97316]' : 'border-gray-200 text-gray-400 hover:text-[#F97316]'}`}><Bookmark size={17} fill={isFavorite ? 'currentColor' : 'none'} /></button>
          <button type="button" disabled={inReading} onClick={onAddReading} title={inReading ? '已在阅读清单' : '加入阅读清单'} className="rounded-lg border border-gray-200 p-2 text-gray-400 transition hover:text-[#F97316] disabled:cursor-default disabled:bg-gray-50 disabled:text-emerald-500"><BookOpenCheck size={17} /></button>
          {sourceUrl && <a href={sourceUrl} target="_blank" rel="noreferrer" title="打开来源" className="rounded-lg border border-gray-200 p-2 text-gray-400 transition hover:text-gray-700"><ExternalLink size={17} /></a>}
        </div>
      </div>
      {paper.abstractZh && <p className="mt-3 line-clamp-2 text-sm leading-6 text-gray-600">{paper.abstractZh}</p>}
    </div>
  );
}

function AuthorDetailPanel({ detail, loading, ...paperProps }: { detail: DiscoveryAuthorDetail | null; loading: boolean } & SharedPaperActions) {
  if (loading) return <LoadingCard />;
  if (!detail) return <EmptyCard label="点击左侧作者查看学术概况与代表论文" />;
  const orcidUrl = safeExternalUrl(detail.orcid);
  return (
    <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div><h2 className="text-xl font-bold text-gray-900">{detail.name}</h2><p className="mt-1 text-sm text-gray-500">{detail.institutions.join(' · ') || '机构信息暂无'}</p></div>
      <div className="grid grid-cols-2 gap-3"><Metric label="论文数量" value={detail.worksCount} /><Metric label="总被引次数" value={detail.citedByCount} /></div>
      {orcidUrl && <a href={orcidUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-[#F97316] hover:underline">ORCID <ExternalLink size={13} /></a>}
      <div><h3 className="mb-3 font-semibold text-gray-900">高影响力代表论文</h3><div className="space-y-3">{detail.topWorks.map((paper) => <CompactPaper key={paper.id} paper={paper} {...paperProps} />)}</div></div>
    </div>
  );
}

function VenueDetailPanel({ detail, loading, ...paperProps }: { detail: DiscoveryVenueDetail | null; loading: boolean } & SharedPaperActions) {
  if (loading) return <LoadingCard />;
  if (!detail) return <EmptyCard label="点击左侧会议 / 期刊查看来源信息与代表论文" />;
  const homepageUrl = safeExternalUrl(detail.homepageUrl);
  return (
    <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div><h2 className="text-xl font-bold text-gray-900">{detail.name}</h2><p className="mt-1 text-sm text-gray-500">{detail.hostOrganization || detail.issn || '出版机构信息暂无'}</p></div>
      <div className="grid grid-cols-2 gap-3"><Metric label="收录论文" value={detail.worksCount} /><Metric label="总被引次数" value={detail.citedByCount} /></div>
      <div className="flex flex-wrap gap-2 text-xs">{detail.type && <Badge>{detail.type}</Badge>}{detail.isOpenAccess && <Badge>Open Access</Badge>}{detail.isInDoaj && <Badge>DOAJ</Badge>}</div>
      {homepageUrl && <a href={homepageUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-[#F97316] hover:underline">访问主页 <ExternalLink size={13} /></a>}
      <div><h3 className="mb-3 font-semibold text-gray-900">高影响力代表论文</h3><div className="space-y-3">{detail.topWorks.map((paper) => <CompactPaper key={paper.id} paper={paper} {...paperProps} />)}</div></div>
    </div>
  );
}

interface SharedPaperActions {
  favoriteIds: Set<string>;
  readingIds: Set<string>;
  onSelectPaper: (paper: Paper) => void;
  onToggleFavorite: (paper: Paper) => void;
  onAddReading: (paper: Paper) => void;
}

function CompactPaper({ paper, favoriteIds, readingIds, onSelectPaper, onToggleFavorite, onAddReading }: { paper: Paper } & SharedPaperActions) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-100 bg-gray-50 p-3">
      <button type="button" onClick={() => onSelectPaper(paper)} className="w-full min-w-0 text-left"><div className="line-clamp-2 break-words text-sm font-medium leading-5 text-gray-900 hover:text-[#F97316]">{paper.titleEn}</div><div className="mt-1 truncate text-xs text-gray-500" title={`${paper.year} · ${paper.venue} · ${paper.citations || 0} 次被引`}>{paper.year} · {paper.venue} · {paper.citations || 0} 次被引</div></button>
      <div className="mt-2 flex gap-2"><button type="button" onClick={() => onToggleFavorite(paper)} className="text-xs text-[#F97316]">{favoriteIds.has(paper.id) ? '取消收藏' : '收藏'}</button><span className="text-gray-300">·</span><button type="button" disabled={readingIds.has(paper.id)} onClick={() => onAddReading(paper)} className="text-xs text-[#F97316] disabled:text-gray-400">{readingIds.has(paper.id) ? '已加入阅读' : '加入阅读'}</button></div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) { return <div className="rounded-lg bg-gray-50 p-3"><div className="text-xl font-bold text-gray-900">{value.toLocaleString()}</div><div className="mt-1 text-xs text-gray-500">{label}</div></div>; }
function Badge({ children }: { children: React.ReactNode }) { return <span className="rounded-full bg-[#FFF7ED] px-2.5 py-1 font-medium text-[#F97316]">{children}</span>; }
function LoadingCard() { return <div className="flex min-h-48 items-center justify-center rounded-xl border border-gray-200 bg-white text-gray-500"><Loader2 className="mr-2 animate-spin" size={18} />正在加载...</div>; }
function EmptyCard({ label }: { label: string }) { return <div className="flex min-h-48 flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white text-center text-sm text-gray-500"><Search className="mb-3 text-gray-300" size={32} /><div>{label}</div></div>; }
