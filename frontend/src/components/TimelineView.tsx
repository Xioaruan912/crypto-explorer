'use client';

import { CalendarDays, ChevronRight } from 'lucide-react';
import { Paper } from '../types/paper';
import { categoryColors } from '../constants/categories';

export default function TimelineView({
  papers,
  activeFilter,
  onSelect,
}: {
  papers: Paper[];
  activeFilter: string;
  onSelect: (id: string) => void;
}) {
  const filtered = papers
    .filter((paper) => activeFilter === 'all' || paper.category === activeFilter)
    .sort((a, b) => b.year - a.year || (b.citations || 0) - (a.citations || 0));
  const groups = Array.from(new Set(filtered.map((paper) => paper.year))).sort((a, b) => b - a);

  return (
    <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">研究时间线</h2>
          <p className="mt-1 text-sm text-gray-500">按年份查看研究演进、代表论文和被引影响。</p>
        </div>
        <div className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-600">{filtered.length} 篇论文</div>
      </div>
      <div className="space-y-8">
        {groups.map((year) => {
          const yearPapers = filtered.filter((paper) => paper.year === year);
          return (
            <section key={year} className="grid grid-cols-[96px_1fr] gap-5">
              <div className="pt-1">
                <div className="text-2xl font-bold text-gray-900">{year}</div>
                <div className="mt-1 text-xs text-gray-400">{yearPapers.length} papers</div>
              </div>
              <div className="relative border-l border-gray-200 pl-6">
                <div className="absolute -left-2 top-2 h-4 w-4 rounded-full border-4 border-white bg-[#F97316] shadow" />
                <div className="space-y-3">
                  {yearPapers.map((paper) => (
                    <button
                      key={paper.id}
                      onClick={() => onSelect(paper.id)}
                      className="group w-full overflow-hidden rounded-xl border border-gray-100 bg-gray-50/70 p-4 text-left transition hover:border-[#FED7AA] hover:bg-[#FFF7ED]"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <div className="mb-2 flex min-w-0 items-center gap-2 text-xs text-gray-500">
                            <span className="h-2 w-2 rounded-full" style={{ background: categoryColors[paper.category] }} />
                            <span className="min-w-0 truncate" title={paper.venue}>{paper.venue}</span>
                            <span>·</span>
                            <span className="shrink-0">{paper.citations || 0} 被引</span>
                          </div>
                          <div className="line-clamp-2 break-words font-medium text-gray-900 group-hover:text-[#F97316]">{paper.titleEn}</div>
                          <div className="mt-1 truncate text-sm text-gray-500">{paper.authors.join(', ')}</div>
                        </div>
                        <ChevronRight className="mt-2 h-4 w-4 shrink-0 text-gray-300 group-hover:text-[#F97316]" />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </section>
          );
        })}
        {groups.length === 0 && (
          <div className="flex h-72 flex-col items-center justify-center text-gray-400">
            <CalendarDays className="mb-3 h-10 w-10" />
            当前筛选下没有论文
          </div>
        )}
      </div>
    </div>
  );
}
