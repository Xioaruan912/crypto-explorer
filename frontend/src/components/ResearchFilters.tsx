'use client';

import React, { useState } from 'react';
import { CalendarRange, ChevronDown } from 'lucide-react';
import { categoryColors } from '../constants/categories';
import { ResearchTimeRange } from '../types/research';

const filters = [
  { id: 'all', label: '全部', color: '#F97316' },
  { id: 'foundation', label: '基础理论', color: categoryColors.foundation },
  { id: 'security', label: '安全性', color: categoryColors.security },
  { id: 'efficiency', label: '效率优化', color: categoryColors.efficiency },
  { id: 'scalability', label: '大规模/扩展性', color: categoryColors.scalability },
  { id: 'variant', label: '变体与扩展', color: categoryColors.variant },
  { id: 'application', label: '应用与实践', color: categoryColors.application },
];

interface ResearchFiltersProps {
  activeFilter: string;
  onFilterChange: (filterId: string) => void;
  timeRange: ResearchTimeRange;
  onTimeRangeChange: (range: ResearchTimeRange) => void;
}

export default function ResearchFilters({ activeFilter, onFilterChange, timeRange, onTimeRangeChange }: ResearchFiltersProps) {
  const [open, setOpen] = useState(false);
  const [fromYear, setFromYear] = useState(timeRange.fromYear ? String(timeRange.fromYear) : '');
  const [toYear, setToYear] = useState(timeRange.toYear ? String(timeRange.toYear) : '');
  const [foundational, setFoundational] = useState(timeRange.strategy === 'foundational');

  const currentYear = new Date().getFullYear();
  const label = timeRange.fromYear || timeRange.toYear
    ? `${timeRange.fromYear || '最早'}–${timeRange.toYear || currentYear}`
    : '全部年份';

  const apply = (range: ResearchTimeRange) => {
    setFromYear(range.fromYear ? String(range.fromYear) : '');
    setToYear(range.toYear ? String(range.toYear) : '');
    setFoundational(range.strategy === 'foundational');
    onTimeRangeChange(range);
    setOpen(false);
  };

  return (
    <div className="flex items-center justify-between gap-4 py-4">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        {filters.map(filter => (
          <button
            key={filter.id}
            onClick={() => onFilterChange(filter.id)}
            className={`rounded-full border px-4 py-1.5 text-sm font-medium transition-colors ${
              activeFilter === filter.id
                ? 'border-[#F97316] bg-[#FFF7ED] text-[#F97316]'
                : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      <div className="relative shrink-0">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
        >
          <CalendarRange size={15} className="text-gray-400" />
          <span>时间范围：{label}</span>
          {timeRange.strategy === 'foundational' && <span className="rounded bg-[#FFF7ED] px-1.5 py-0.5 text-[10px] text-[#F97316]">基础优先</span>}
          <ChevronDown size={16} className="text-gray-400" />
        </button>

        {open && (
          <div className="absolute right-0 top-11 z-40 w-[340px] rounded-xl border border-gray-200 bg-white p-4 shadow-xl">
            <div className="mb-3 text-sm font-semibold text-gray-900">研究时间范围</div>
            <div className="grid grid-cols-3 gap-2">
              <PresetButton label="全部年份" onClick={() => apply({ strategy: 'relevance' })} />
              <PresetButton label="近 10 年" onClick={() => apply({ fromYear: currentYear - 9, toYear: currentYear, strategy: 'relevance' })} />
              <PresetButton label="经典基础" onClick={() => apply({ fromYear: 1900, toYear: 2005, strategy: 'foundational' })} />
            </div>
            <div className="my-4 border-t border-gray-100" />
            <div className="grid grid-cols-2 gap-3">
              <label className="text-xs font-medium text-gray-500">起始年份
                <input type="number" min="1800" max="2100" value={fromYear} onChange={(e) => setFromYear(e.target.value)} placeholder="例如 1940" className="mt-1.5 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#F97316]" />
              </label>
              <label className="text-xs font-medium text-gray-500">结束年份
                <input type="number" min="1800" max="2100" value={toYear} onChange={(e) => setToYear(e.target.value)} placeholder={String(currentYear)} className="mt-1.5 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#F97316]" />
              </label>
            </div>
            <label className="mt-3 flex items-start gap-2 rounded-lg bg-gray-50 p-3 text-xs leading-5 text-gray-600">
              <input type="checkbox" checked={foundational} onChange={(e) => setFoundational(e.target.checked)} className="mt-1" />
              <span><strong className="text-gray-800">基础论文优先</strong><br />在设定年代里优先选择高影响力、与主题相关的早期论文作为图谱起点。</span>
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setOpen(false)} className="rounded-lg px-3 py-2 text-sm text-gray-500 hover:bg-gray-50">取消</button>
              <button
                type="button"
                onClick={() => apply({
                  fromYear: fromYear ? Number(fromYear) : undefined,
                  toYear: toYear ? Number(toYear) : undefined,
                  strategy: foundational ? 'foundational' : 'relevance',
                })}
                className="rounded-lg bg-[#F97316] px-4 py-2 text-sm font-medium text-white hover:bg-orange-600"
              >
                应用范围
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function PresetButton({ label, onClick }: { label: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} className="rounded-lg border border-gray-200 bg-gray-50 px-2 py-2 text-xs font-medium text-gray-600 hover:border-[#FDBA74] hover:bg-[#FFF7ED] hover:text-[#F97316]">{label}</button>;
}
