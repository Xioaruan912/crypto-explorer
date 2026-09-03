'use client';

import { Languages } from 'lucide-react';
import { QueryInfo, SearchLanguageMode } from '@/types/research';

export function SearchLanguageToggle({
  mode,
  onChange,
  compact = false,
}: {
  mode: SearchLanguageMode;
  onChange: (mode: SearchLanguageMode) => void;
  compact?: boolean;
}) {
  return (
    <div className={`flex items-center rounded-lg border border-gray-200 bg-white p-1 ${compact ? 'shrink-0' : 'w-fit'}`}>
      <Languages size={14} className="mx-1.5 text-gray-400" />
      <button
        type="button"
        onClick={() => onChange('academic_en')}
        className={`rounded-md px-2.5 py-1.5 text-xs font-medium transition ${mode === 'academic_en' ? 'bg-[#FFF7ED] text-[#F97316]' : 'text-gray-500 hover:bg-gray-50'}`}
        title="检测到中文密码学术语时，转换为常用英文学术检索词"
      >
        中文→英文
      </button>
      <button
        type="button"
        onClick={() => onChange('original')}
        className={`rounded-md px-2.5 py-1.5 text-xs font-medium transition ${mode === 'original' ? 'bg-[#FFF7ED] text-[#F97316]' : 'text-gray-500 hover:bg-gray-50'}`}
        title="完全使用你输入的原始关键词"
      >
        原词
      </button>
    </div>
  );
}

export function QueryLanguageNotice({ info, className = '' }: { info: QueryInfo | null | undefined; className?: string }) {
  if (!info) return null;
  const changed = info.translated && info.effectiveQuery.trim().toLowerCase() !== info.originalQuery.trim().toLowerCase();
  return (
    <div className={`rounded-lg border border-[#FED7AA] bg-[#FFF7ED] px-3 py-2.5 text-xs text-gray-600 ${className}`}>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <Languages size={14} className="text-[#F97316]" />
        <span>{info.notice}</span>
        {changed && (
          <>
            <span className="text-gray-300">·</span>
            <span className="text-gray-400">实际检索：</span>
            <span className="font-semibold text-[#F97316]">{info.effectiveQuery}</span>
          </>
        )}
      </div>
      {info.historicalTerms.length > 0 && (
        <div className="mt-1.5 truncate text-[11px] text-gray-400" title={info.historicalTerms.join(' · ')}>
          历史术语辅助：{info.historicalTerms.join(' · ')}
        </div>
      )}
    </div>
  );
}
