'use client';

import { useEffect, useState } from 'react';
import { ArrowDown, BookOpenCheck, ChevronDown, ExternalLink, GitBranch, Loader2, Search, Sparkles } from 'lucide-react';
import { genealogyService } from '@/services/genealogyService';
import { GenealogyData, GenealogyPaper, ResearchTimeRange, SearchLanguageMode, StudyMode } from '@/types/research';
import { Paper } from '@/types/paper';

interface Props {
  query: string;
  mode: Exclude<StudyMode, 'related'>;
  range: ResearchTimeRange;
  searchLanguageMode: SearchLanguageMode;
  readingIds: Set<string>;
  onSelectPaper: (paper: Paper) => void;
  onAddReading: (paper: Paper) => Promise<void>;
}

export default function GenealogyView({ query, mode, range, searchLanguageMode, readingIds, onSelectPaper, onAddReading }: Props) {
  const [data, setData] = useState<GenealogyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showBackground, setShowBackground] = useState(false);

  useEffect(() => {
    let active = true;
    genealogyService.getGenealogy(query, range, searchLanguageMode)
      .then((result) => { if (active) setData(result); })
      .catch((e) => { if (active) setError(e instanceof Error ? e.message : '概念谱系加载失败'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [query, range, searchLanguageMode]);

  if (loading) return <div className="mt-6 flex h-[460px] items-center justify-center rounded-xl border border-gray-200 bg-white text-gray-500"><Loader2 size={22} className="mr-2 animate-spin text-[#F97316]" />正在沿参考文献反向追溯概念祖先...</div>;
  if (error) return <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-600">{error}</div>;
  if (!data) return null;

  if (mode === 'origin') {
    return <div className="mt-6 space-y-5">
      <div className="rounded-xl border border-[#FED7AA] bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div><div className="flex items-center gap-2 text-sm font-semibold text-[#F97316]"><Sparkles size={17} />开山论文候选</div><p className="mt-1 text-sm text-gray-500">不是找标题里最早出现关键词的论文，而是结合现代锚点、反向引用祖先、年代和学术影响力寻找概念源头。</p>{data.historicalQuery && <p className="mt-2 text-xs text-[#F97316]">历史术语辅助：{data.historicalQuery}</p>}</div>
          <div className="rounded-lg bg-[#FFF7ED] px-3 py-2 text-xs text-[#F97316]">基础池 {data.poolCount} 篇</div>
        </div>
        {data.origin ? <OriginCard item={data.origin} inReading={readingIds.has(data.origin.paper.id)} onSelect={onSelectPaper} onAddReading={onAddReading} /> : <div className="py-16 text-center text-gray-400">暂时无法确认开山论文</div>}
      </div>
      {!!data.background.length && <div className="rounded-xl border border-gray-200 bg-white p-5">
        <button onClick={() => setShowBackground((value) => !value)} className="flex w-full items-center justify-between text-left"><div><div className="flex items-center gap-2 font-semibold text-gray-900"><GitBranch size={18} className="text-[#F97316]" />查看更早理论背景</div><p className="mt-1 text-xs text-gray-400">默认不把开山论文之前的数学/密码学背景混进主学习路线。</p></div><ChevronDown size={18} className={`text-gray-400 transition ${showBackground ? 'rotate-180' : ''}`} /></button>
        {showBackground && <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">{data.background.slice(0, 6).map((item) => <MiniCard key={item.paper.id} item={item} onClick={() => onSelectPaper(item.paper)} />)}</div>}
      </div>}
    </div>;
  }

  return <div className="mt-6 space-y-3">
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
    <div className="mb-6"><div className="flex items-center gap-2 text-lg font-bold text-gray-900"><GitBranch size={20} className="text-[#F97316]" />从开山开始学：{query}</div><p className="mt-1 text-sm text-gray-500">先确定概念源头，再沿 cited-by 向未来组织“开山论文 → 早期奠基 → 关键演进 → 现代代表”。主线年份只向前，不再把更晚论文放在开山之前。</p></div>
    <div className="space-y-3">
      {data.learningPath.map((stage, index) => <div key={stage.stage}>
        <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-4 rounded-xl border border-gray-100 bg-gray-50/50 p-4">
          <div><div className="text-xs text-gray-400">STEP {index + 1}</div><div className="mt-1 font-semibold text-[#F97316]">{stage.stage}</div></div>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">{stage.papers.length ? stage.papers.map((item) => <LearningCard key={item.paper.id} item={item} inReading={readingIds.has(item.paper.id)} onSelect={onSelectPaper} onAddReading={onAddReading} />) : <div className="rounded-lg border border-dashed border-gray-200 bg-white p-5 text-sm text-gray-400">当前数据源没有找到足够明确的这一阶段论文</div>}</div>
        </div>
        {index < data.learningPath.length - 1 && <div className="flex h-8 items-center pl-[54px] text-gray-300"><ArrowDown size={18} /></div>}
      </div>)}
    </div>
    {!!data.branches.length && <div className="mt-6 border-t border-gray-100 pt-5"><div className="mb-3 text-sm font-semibold text-gray-900">重要分支</div><div className="grid gap-3 lg:grid-cols-2">{data.branches.map((branch) => <div key={branch.name} className="rounded-xl border border-gray-100 bg-gray-50/50 p-4"><div className="mb-3 text-xs font-semibold text-[#F97316]">{branch.name}</div><div className="space-y-2">{branch.papers.map((item) => <MiniCard key={item.paper.id} item={item} onClick={() => onSelectPaper(item.paper)} />)}</div></div>)}</div></div>}
    {!!data.background.length && <div className="mt-6 border-t border-gray-100 pt-5"><button onClick={() => setShowBackground((value) => !value)} className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-[#F97316]"><ChevronDown size={16} className={`transition ${showBackground ? 'rotate-180' : ''}`} />查看开山论文之前的理论背景（{data.background.length}）</button>{showBackground && <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-3">{data.background.slice(0, 6).map((item) => <MiniCard key={item.paper.id} item={item} onClick={() => onSelectPaper(item.paper)} />)}</div>}</div>}
    </div>
  </div>;
}

function OriginCard({ item, inReading, onSelect, onAddReading }: { item: GenealogyPaper; inReading: boolean; onSelect: (paper: Paper) => void; onAddReading: (paper: Paper) => Promise<void> }) {
  const p = item.paper;
  return <div className="rounded-xl border border-[#FDBA74] bg-[#FFFBEB] p-5">
    <div className="flex items-start gap-5"><div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-[#FFEDD5] text-[#F97316]"><Search size={26} /></div><div className="min-w-0 flex-1"><div className="text-xs font-semibold text-[#F97316]">{p.year} · {p.venue}</div>{p.sourceYear && p.sourceYear !== p.year && <div className="mt-1 text-[11px] text-amber-600">年份已从数据源的 {p.sourceYear} 校正为 {p.year} · {p.canonicalSource || '规范元数据'}</div>}<h2 className="mt-1 text-xl font-bold leading-7 text-gray-900">{p.titleEn}</h2><div className="mt-2 truncate text-sm text-gray-500">{p.authors.join(', ')}</div><p className="mt-4 rounded-lg bg-white p-3 text-sm leading-6 text-gray-600">{item.reason}</p><div className="mt-4 flex gap-2"><button onClick={() => onSelect(p)} className="rounded-lg border border-[#FDBA74] bg-white px-4 py-2 text-sm font-medium text-[#F97316]">查看论文详情</button><button disabled={inReading} onClick={() => onAddReading(p)} className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm text-gray-600 disabled:text-emerald-600"><BookOpenCheck size={15} />{inReading ? '已在阅读清单' : '加入阅读清单'}</button></div></div></div>
  </div>;
}

function LearningCard({ item, inReading, onSelect, onAddReading }: { item: GenealogyPaper; inReading: boolean; onSelect: (paper: Paper) => void; onAddReading: (paper: Paper) => Promise<void> }) {
  const p = item.paper;
  return <div className="rounded-lg border border-gray-200 bg-white p-4"><div className="text-xs text-gray-400">{p.year} · {p.venue}</div>{p.sourceYear && p.sourceYear !== p.year && <div className="mt-1 text-[10px] text-amber-600">原数据 {p.sourceYear} → 校正 {p.year}</div>}<button onClick={() => onSelect(p)} className="mt-1 line-clamp-2 text-left text-sm font-semibold leading-5 text-gray-900 hover:text-[#F97316]">{p.titleEn}</button><div className="mt-2 truncate text-xs text-gray-500">{p.authors.join(', ')}</div><p className="mt-3 line-clamp-2 text-xs leading-5 text-gray-500">{item.reason}</p><div className="mt-3 flex gap-3 text-xs"><button onClick={() => onSelect(p)} className="text-[#F97316]">查看详情</button><button disabled={inReading} onClick={() => onAddReading(p)} className="text-[#F97316] disabled:text-emerald-600">{inReading ? '已加入' : '加入阅读'}</button></div></div>;
}

function MiniCard({ item, onClick }: { item: GenealogyPaper; onClick: () => void }) {
  return <button onClick={onClick} className="min-w-0 rounded-lg border border-gray-100 bg-gray-50 p-4 text-left hover:border-[#FED7AA] hover:bg-[#FFFBEB]"><div className="text-xs text-gray-400">{item.paper.year}</div><div className="mt-1 line-clamp-2 text-sm font-semibold text-gray-900">{item.paper.titleEn}</div><div className="mt-2 line-clamp-2 text-xs leading-5 text-gray-500">{item.reason}</div><ExternalLink size={13} className="mt-3 text-[#F97316]" /></button>;
}
