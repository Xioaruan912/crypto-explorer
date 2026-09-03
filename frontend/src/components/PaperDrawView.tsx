'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { BookOpenCheck, CalendarDays, Check, Dice5, History, Loader2, NotebookPen, RefreshCw, Search, Trash2 } from 'lucide-react';
import { genealogyService } from '@/services/genealogyService';
import { researchService } from '@/services/researchService';
import { DrawHistoryItem, GenealogyPaper } from '@/types/research';
import { Paper } from '@/types/paper';
import { getWeekDays, startOfWeek } from '@/utils/week';

const topics = [
  ['全部', 'cryptography'], ['对称加密', 'symmetric encryption'], ['公钥密码', 'public key cryptography'],
  ['零知识', 'zero knowledge proofs'], ['MPC', 'secure multiparty computation'], ['格密码', 'lattice cryptography'], ['哈希函数', 'cryptographic hash functions'],
] as const;

interface Props {
  readingIds: Set<string>;
  onSelectPaper: (paper: Paper) => void;
  onAddReading: (paper: Paper) => Promise<void>;
}

export default function PaperDrawView({ readingIds, onSelectPaper, onAddReading }: Props) {
  const [query, setQuery] = useState('cryptography');
  const [customQuery, setCustomQuery] = useState('');
  const [rangeMode, setRangeMode] = useState<'all' | 'classic' | 'custom'>('all');
  const [fromYear, setFromYear] = useState(1900);
  const [toYear, setToYear] = useState(new Date().getFullYear());
  const [foundationalOnly, setFoundationalOnly] = useState(true);
  const [history, setHistory] = useState<DrawHistoryItem[]>([]);
  const [reel, setReel] = useState<GenealogyPaper[]>([]);
  const [selected, setSelected] = useState<GenealogyPaper | null>(null);
  const [pending, setPending] = useState<GenealogyPaper | null>(null);
  const [poolCount, setPoolCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [spinning, setSpinning] = useState(false);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState('');
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [scheduled, setScheduled] = useState('');
  const viewportRef = useRef<HTMLDivElement>(null);
  const weekDays = useMemo(() => getWeekDays(startOfWeek(new Date())), []);

  useEffect(() => { genealogyService.history().then(setHistory).catch(() => undefined); }, []);

  const effectiveQuery = customQuery.trim() || query;
  const activeRange = rangeMode === 'classic' ? { fromYear: 1900, toYear: 2005 } : rangeMode === 'custom' ? { fromYear, toYear } : {};
  const displayReel = useMemo(() => {
    if (!reel.length) return [];
    const base = reel.slice(0, -1);
    return [...base, ...base, ...base, reel[reel.length - 1]];
  }, [reel]);

  const draw = async () => {
    if (effectiveQuery.length < 2) return setError('请输入至少 2 个字符的研究主题');
    setLoading(true); setError(''); setSelected(null); setScheduled(''); setScheduleOpen(false); setOffset(0); setSpinning(false);
    try {
      const result = await genealogyService.draw({ query: effectiveQuery, ...activeRange, foundationalOnly });
      setPoolCount(result.poolCount);
      setReel(result.reel);
      setPending(result.selected);
      setHistory((current) => [result.historyItem, ...current.filter((item) => item.id !== result.historyItem.id)].slice(0, 20));
      requestAnimationFrame(() => requestAnimationFrame(() => {
        const cardWidth = 188;
        const targetIndex = Math.max(0, (result.reel.length - 1) * 3);
        const viewport = viewportRef.current?.clientWidth || 900;
        setSpinning(true);
        setOffset(Math.max(0, targetIndex * cardWidth - viewport / 2 + 88));
        window.setTimeout(() => { setSelected(result.selected); setPending(null); setSpinning(false); }, 2600);
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : '抽取失败');
    } finally { setLoading(false); }
  };

  const schedule = async (iso: string) => {
    if (!selected) return;
    try {
      if (!readingIds.has(selected.paper.id)) await onAddReading(selected.paper);
      await researchService.createReadingTask({ paperId: selected.paper.id, scheduledDate: iso, taskType: 'read', taskText: `阅读：${selected.paper.titleEn}` });
      setScheduled(iso); setScheduleOpen(false);
    } catch (e) { setError(e instanceof Error ? e.message : '安排阅读任务失败'); }
  };

  return <div className="space-y-4">
    <div><div className="flex items-center gap-2 text-sm font-semibold text-[#6D4AFF]"><Dice5 size={18} />研究工作区</div><h1 className="mt-1 text-2xl font-bold text-gray-900">基础理论论文抽取</h1><p className="mt-1 text-sm text-gray-500">先构建主题的概念谱系和基础论文池，再从池中均匀随机抽取；没有稀有度和等级。</p></div>

    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center gap-2 font-semibold text-gray-900"><Search size={17} className="text-[#6D4AFF]" />抽取设置 <span className="text-xs font-normal text-gray-400">仅从基础理论候选池中随机</span></div>
      <div className="space-y-4 text-sm">
        <div className="flex items-center gap-3"><span className="w-16 shrink-0 text-gray-500">研究方向</span><div className="flex flex-wrap gap-2">{topics.map(([label, value]) => <button key={value} onClick={() => { setQuery(value); setCustomQuery(''); }} className={`rounded-lg border px-4 py-2 ${!customQuery && query === value ? 'border-[#B8A8FF] bg-[#F7F5FF] text-[#6D4AFF]' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>{label}</button>)}<input value={customQuery} onChange={(e) => setCustomQuery(e.target.value)} placeholder="自定义主题，例如 Anamorphic Encryption" className="min-w-[280px] rounded-lg border border-gray-200 px-3 py-2 outline-none focus:border-[#B8A8FF]" /></div></div>
        <div className="flex items-center gap-3"><span className="w-16 shrink-0 text-gray-500">时间范围</span><div className="flex flex-wrap items-center gap-2"><button onClick={() => setRangeMode('all')} className={`rounded-lg border px-4 py-2 ${rangeMode === 'all' ? 'border-[#B8A8FF] bg-[#F7F5FF] text-[#6D4AFF]' : 'border-gray-200 text-gray-600'}`}>全部年份</button><button onClick={() => setRangeMode('classic')} className={`rounded-lg border px-4 py-2 ${rangeMode === 'classic' ? 'border-[#B8A8FF] bg-[#F7F5FF] text-[#6D4AFF]' : 'border-gray-200 text-gray-600'}`}>经典基础</button><button onClick={() => setRangeMode('custom')} className={`rounded-lg border px-4 py-2 ${rangeMode === 'custom' ? 'border-[#B8A8FF] bg-[#F7F5FF] text-[#6D4AFF]' : 'border-gray-200 text-gray-600'}`}>自定义</button>{rangeMode === 'custom' && <div className="flex items-center gap-2"><input type="number" min={1800} max={2100} value={fromYear} onChange={(e) => setFromYear(Number(e.target.value))} className="w-24 rounded-lg border border-gray-200 px-2 py-2" /><span className="text-gray-300">—</span><input type="number" min={1800} max={2100} value={toYear} onChange={(e) => setToYear(Number(e.target.value))} className="w-24 rounded-lg border border-gray-200 px-2 py-2" /></div>}</div><label className="ml-auto flex items-center gap-2 text-gray-600"><span>基础论文优先</span><button onClick={() => setFoundationalOnly((v) => !v)} className={`relative h-6 w-11 rounded-full transition ${foundationalOnly ? 'bg-[#6D4AFF]' : 'bg-gray-200'}`}><span className={`absolute top-1 h-4 w-4 rounded-full bg-white transition ${foundationalOnly ? 'left-6' : 'left-1'}`} /></button></label></div>
      </div>
    </div>

    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between"><div className="font-semibold text-gray-900">随机抽取</div><div className="text-xs text-gray-400">{poolCount ? `本次基础池 ${poolCount} 篇` : '等待构建基础论文池'}</div></div>
      <div ref={viewportRef} className="relative overflow-hidden rounded-xl border border-gray-100 bg-[#FBFBFD] py-5">
        <div className="pointer-events-none absolute left-1/2 top-0 z-10 h-full w-px bg-[#6D4AFF]"><span className="absolute -left-2 -top-1 border-x-[8px] border-t-[10px] border-x-transparent border-t-[#6D4AFF]" /></div>
        {displayReel.length ? <div className="flex gap-3 px-5" style={{ transform: `translateX(-${offset}px)`, transition: spinning ? 'transform 2.5s cubic-bezier(.08,.62,.12,1)' : 'none' }}>{displayReel.map((item, index) => <ReelCard key={`${item.paper.id}-${index}`} item={item} />)}</div> : <div className="flex h-40 items-center justify-center text-sm text-gray-400">点击“开始抽取”，系统会先追溯概念祖先并生成候选池</div>}
      </div>
      <div className="mt-4 flex justify-center gap-3"><button disabled={loading || spinning} onClick={draw} className="flex min-w-44 items-center justify-center gap-2 rounded-lg bg-[#6D4AFF] px-6 py-2.5 text-sm font-semibold text-white hover:bg-purple-700 disabled:opacity-50">{loading ? <Loader2 size={16} className="animate-spin" /> : <Dice5 size={16} />}{loading ? '正在构建基础池...' : spinning ? '正在抽取...' : selected ? '重新抽取' : '开始抽取'}</button>{selected && <button disabled={spinning} onClick={draw} className="flex items-center gap-2 rounded-lg border border-gray-200 px-5 py-2.5 text-sm text-gray-600"><RefreshCw size={15} />再抽一次</button>}</div>
      {error && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">{error}</div>}
    </div>

    {(selected || pending) && <div className="grid grid-cols-[minmax(0,1fr)_360px] gap-4">
      <div className={`rounded-xl border bg-white p-5 ${selected ? 'border-[#CFC3FF]' : 'border-gray-200 opacity-60'}`}><div className="mb-4 text-sm font-semibold text-gray-900">本次抽取结果</div>{selected ? <ResultCard item={selected} scheduled={scheduled} scheduleOpen={scheduleOpen} setScheduleOpen={setScheduleOpen} weekDays={weekDays} onSchedule={schedule} onSelectPaper={onSelectPaper} onAddReading={onAddReading} inReading={readingIds.has(selected.paper.id)} /> : <div className="flex h-48 items-center justify-center text-gray-400"><Loader2 className="mr-2 animate-spin" />卡片正在停止...</div>}</div>
      <HistoryPanel items={history} onClear={async () => { await genealogyService.clearHistory(); setHistory([]); }} onSelect={(paper) => onSelectPaper(paper)} />
    </div>}
    {!selected && !pending && <HistoryPanel items={history} onClear={async () => { await genealogyService.clearHistory(); setHistory([]); }} onSelect={onSelectPaper} wide />}
  </div>;
}

function ReelCard({ item }: { item: GenealogyPaper }) { const p = item.paper; return <div className="h-40 w-44 shrink-0 rounded-lg border border-gray-200 bg-white p-3 shadow-sm"><div className="text-[11px] text-gray-400">{p.year} · <span className="max-w-24 truncate">{p.venue}</span></div><div className="mt-2 line-clamp-4 text-sm font-semibold leading-5 text-gray-900">{p.titleEn}</div><div className="mt-3 truncate text-[11px] text-gray-400">{p.authors.join(', ')}</div></div>; }

function ResultCard({ item, scheduled, scheduleOpen, setScheduleOpen, weekDays, onSchedule, onSelectPaper, onAddReading, inReading }: { item: GenealogyPaper; scheduled: string; scheduleOpen: boolean; setScheduleOpen: (value: boolean) => void; weekDays: ReturnType<typeof getWeekDays>; onSchedule: (iso: string) => Promise<void>; onSelectPaper: (paper: Paper) => void; onAddReading: (paper: Paper) => Promise<void>; inReading: boolean }) {
  const p = item.paper;
  return <div><div className="flex items-start gap-4"><div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-[#F2EFFF] text-[#6D4AFF]"><Dice5 size={24} /></div><div className="min-w-0"><h2 className="text-lg font-bold leading-7 text-gray-900">{p.titleEn}</h2><div className="mt-1 truncate text-sm text-gray-500">{p.authors.join(', ')}</div><div className="mt-2 text-xs text-gray-400">{p.year} · {p.venue} · {(p.citations || 0).toLocaleString()} 次被引</div></div></div><div className="mt-4 rounded-lg bg-[#FAF9FF] p-3 text-sm leading-6 text-gray-600"><span className="font-medium text-[#6D4AFF]">为什么进入基础池：</span>{item.reason}</div><div className="mt-4 flex flex-wrap gap-2"><button onClick={() => onSelectPaper(p)} className="rounded-lg border border-[#CFC3FF] px-4 py-2 text-sm font-medium text-[#6D4AFF]">查看论文详情</button><button disabled={inReading} onClick={() => onAddReading(p)} className="flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600 disabled:text-emerald-600"><BookOpenCheck size={15} />{inReading ? '已在阅读清单' : '加入阅读清单'}</button><div className="relative"><button onClick={() => setScheduleOpen(!scheduleOpen)} className="flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600"><CalendarDays size={15} />{scheduled ? '已安排本周' : '安排本周 TODO'}</button>{scheduleOpen && <div className="absolute bottom-11 left-0 z-20 w-64 rounded-xl border border-gray-200 bg-white p-3 shadow-xl"><div className="mb-2 text-xs font-semibold text-gray-500">选择阅读日期</div><div className="grid grid-cols-7 gap-1">{weekDays.map((day) => <button key={day.iso} onClick={() => onSchedule(day.iso)} className="rounded-lg px-1 py-2 text-center text-[10px] hover:bg-[#F2EFFF] hover:text-[#6D4AFF]"><span className="block font-medium">{day.weekday}</span><span className="mt-1 block text-gray-400">{day.shortDate}</span></button>)}</div></div>}</div><button onClick={() => onSelectPaper(p)} className="flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600"><NotebookPen size={15} />写 Markdown 笔记</button>{scheduled && <span className="flex items-center gap-1 px-2 text-xs text-emerald-600"><Check size={14} />{scheduled}</span>}</div></div>;
}

function HistoryPanel({ items, onClear, onSelect, wide = false }: { items: DrawHistoryItem[]; onClear: () => Promise<void>; onSelect: (paper: Paper) => void; wide?: boolean }) {
  return <div className={`rounded-xl border border-gray-200 bg-white p-5 ${wide ? '' : ''}`}><div className="mb-3 flex items-center justify-between"><div className="flex items-center gap-2 font-semibold text-gray-900"><History size={17} className="text-[#6D4AFF]" />最近抽取</div><button disabled={!items.length} onClick={onClear} className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-500 disabled:opacity-30"><Trash2 size={13} />清空</button></div>{items.length ? <div className={wide ? 'grid grid-cols-2 gap-2 lg:grid-cols-4' : 'space-y-2'}>{items.slice(0, wide ? 8 : 6).map((item) => <button key={item.id} onClick={() => onSelect(item.paper)} className="w-full rounded-lg border border-gray-100 p-3 text-left hover:border-[#CFC3FF]"><div className="line-clamp-2 text-xs font-semibold leading-5 text-gray-800">{item.paper.titleEn}</div><div className="mt-1 text-[10px] text-gray-400">{item.paper.year} · {item.query}</div></button>)}</div> : <div className="py-8 text-center text-sm text-gray-400">还没有抽取记录</div>}</div>;
}
