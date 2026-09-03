'use client';

import { ArrowDownRight, GitMerge, MousePointer2 } from 'lucide-react';
import { GraphData } from '../services/paperService';
import { categoryColors } from '../constants/categories';

export default function CitationNetworkView({
  graphData,
  selectedPaperId,
  onSelect,
}: {
  graphData: GraphData;
  selectedPaperId: string | null;
  onSelect: (id: string) => void;
}) {
  const degree = new Map<string, { incoming: number; outgoing: number }>();
  graphData.papers.forEach((paper) => degree.set(paper.id, { incoming: 0, outgoing: 0 }));
  graphData.edges.forEach((edge) => {
    const source = degree.get(edge.source);
    const target = degree.get(edge.target);
    if (source) source.outgoing += 1;
    if (target) target.incoming += 1;
  });
  const ranked = [...graphData.papers].sort((a, b) => {
    const da = degree.get(a.id)!;
    const db = degree.get(b.id)!;
    return db.incoming + db.outgoing - (da.incoming + da.outgoing) || (b.citations || 0) - (a.citations || 0);
  });
  const selected = graphData.papers.find((paper) => paper.id === selectedPaperId) || ranked[0];
  const relatedIds = new Set(
    graphData.edges
      .filter((edge) => edge.source === selected?.id || edge.target === selected?.id)
      .flatMap((edge) => [edge.source, edge.target]),
  );
  const related = graphData.papers.filter((paper) => relatedIds.has(paper.id) && paper.id !== selected?.id);

  return (
    <div className="mt-6 grid grid-cols-[1.35fr_.65fr] gap-5">
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">引文网络</h2>
            <p className="mt-1 text-sm text-gray-500">按网络连接度识别关键论文，点击节点查看上下游关系。</p>
          </div>
          <GitMerge className="text-[#6D4AFF]" />
        </div>
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-3">
          {ranked.map((paper) => {
            const stats = degree.get(paper.id)!;
            const active = paper.id === selected?.id;
            return (
              <button
                key={paper.id}
                onClick={() => onSelect(paper.id)}
                className={`rounded-xl border p-4 text-left transition ${active ? 'border-[#6D4AFF] bg-[#F7F5FF] shadow-sm' : 'border-gray-100 bg-gray-50 hover:border-gray-200'}`}
              >
                <div className="mb-3 flex items-center justify-between">
                  <span className="h-3 w-3 rounded-full" style={{ background: categoryColors[paper.category] }} />
                  <span className="text-xs text-gray-400">{paper.year}</span>
                </div>
                <div className="line-clamp-3 min-h-[60px] text-sm font-medium text-gray-900">{paper.titleEn}</div>
                <div className="mt-4 flex gap-3 text-xs text-gray-500">
                  <span>入 {stats.incoming}</span>
                  <span>出 {stats.outgoing}</span>
                  <span>{paper.citations || 0} 被引</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
      <aside className="rounded-xl border border-gray-200 bg-white p-5">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
          <MousePointer2 size={16} className="text-[#6D4AFF]" /> 当前节点
        </div>
        {selected ? (
          <>
            <div className="text-base font-semibold leading-6 text-gray-900">{selected.titleEn}</div>
            <div className="mt-2 text-sm text-gray-500">{selected.authors.join(', ')}</div>
            <div className="mt-5 border-t border-gray-100 pt-4">
              <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">直接关联</div>
              <div className="space-y-2">
                {related.map((paper) => (
                  <button key={paper.id} onClick={() => onSelect(paper.id)} className="flex w-full items-start gap-2 rounded-lg p-2 text-left hover:bg-gray-50">
                    <ArrowDownRight className="mt-0.5 h-4 w-4 shrink-0 text-gray-300" />
                    <span className="line-clamp-2 text-sm text-gray-600">{paper.titleEn}</span>
                  </button>
                ))}
                {related.length === 0 && <div className="text-sm text-gray-400">当前子图没有直接关联节点。</div>}
              </div>
            </div>
          </>
        ) : <div className="text-sm text-gray-400">请选择节点</div>}
      </aside>
    </div>
  );
}
