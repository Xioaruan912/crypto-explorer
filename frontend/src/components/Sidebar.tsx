 'use client';

import React from 'react';
import { 
  Network, Clock, GitMerge, BookOpen, 
  Search, Users, Building2, 
  FileText, Bookmark, PenTool,
  Download
} from 'lucide-react';
import { GraphData } from '../services/paperService';
import { ResearchView, WorkspaceSection } from '../types/research';

interface SidebarProps {
  graphData: GraphData | null;
  viewMode: ResearchView;
  readingCount: number;
  favoriteCount: number;
  activeWorkspace?: WorkspaceSection | null;
  timeRangeLabel?: string;
  onViewModeChange: (mode: ResearchView) => void;
  onWorkspaceChange?: (section: WorkspaceSection) => void;
}

export default function Sidebar({ graphData, viewMode, readingCount, favoriteCount, activeWorkspace, timeRangeLabel, onViewModeChange, onWorkspaceChange }: SidebarProps) {
  const papers = graphData?.papers || [];
  const years = papers.map((paper) => paper.year).filter(Boolean);
  const timeRange = timeRangeLabel || (years.length > 0 ? `${Math.min(...years)}–${Math.max(...years)}` : '—');
  const totalCitations = papers.reduce((sum, paper) => sum + (paper.citations || 0), 0);
  const categories = new Set(papers.map((paper) => paper.category)).size;

  const exportReport = () => {
    if (!graphData) return;
    const blob = new Blob([JSON.stringify(graphData, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `crypto-explorer-${new Date().toISOString().slice(0, 10)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <aside className="w-[230px] bg-white border-r border-gray-200 flex flex-col h-full shrink-0">
      <div className="p-3">
        <button onClick={() => onWorkspaceChange?.('dashboard')} className={`w-full px-3 py-2 rounded-md font-medium text-sm flex items-center gap-2 transition-colors ${activeWorkspace === 'dashboard' ? 'bg-[#E9E3FF] text-[#6D4AFF]' : 'bg-[#F2EFFF] text-[#6D4AFF] hover:bg-[#ECE7FF]'}`}>
          <Network size={18} />
          概览
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-4">
          <h3 className="text-xs font-semibold text-gray-400 tracking-wider mb-3">研究功能</h3>
          <div className="space-y-1">
            <NavItem icon={<Network size={18} />} label="文献图谱" active={viewMode === 'graph'} onClick={() => onViewModeChange('graph')} />
            <NavItem icon={<Clock size={18} />} label="时间线" active={viewMode === 'timeline'} onClick={() => onViewModeChange('timeline')} />
            <NavItem icon={<GitMerge size={18} />} label="引文网络" active={viewMode === 'citations'} onClick={() => onViewModeChange('citations')} />
            <NavItem icon={<BookOpen size={18} />} label="阅读清单" badge={readingCount} active={viewMode === 'reading'} onClick={() => onViewModeChange('reading')} />
          </div>
        </div>

        <div className="px-6 py-2">
          <h3 className="text-xs font-semibold text-gray-400 tracking-wider mb-3">检索工具</h3>
          <div className="space-y-1">
            <NavItem icon={<Search size={18} />} label="论文检索" active={viewMode === 'papers'} onClick={() => onViewModeChange('papers')} />
            <NavItem icon={<Users size={18} />} label="作者检索" active={viewMode === 'authors'} onClick={() => onViewModeChange('authors')} />
            <NavItem icon={<Building2 size={18} />} label="会议/期刊检索" active={viewMode === 'venues'} onClick={() => onViewModeChange('venues')} />
          </div>
        </div>

        <div className="px-6 py-4">
          <h3 className="text-xs font-semibold text-gray-400 tracking-wider mb-3">我的资料库</h3>
          <div className="space-y-1">
            <NavItem icon={<FileText size={18} />} label="我的论文" disabled />
            <NavItem icon={<Bookmark size={18} />} label="我的收藏" badge={favoriteCount} active={activeWorkspace === 'favorites'} onClick={() => onWorkspaceChange?.('favorites')} />
            <NavItem icon={<PenTool size={18} />} label="笔记" active={activeWorkspace === 'notes'} onClick={() => onWorkspaceChange?.('notes')} />
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-gray-100">
        <div className="bg-gray-50 rounded-xl p-4 border border-gray-100 shadow-sm">
          <h4 className="font-semibold text-sm text-gray-900 mb-4">研究概览</h4>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <Stat label="论文总数" value={papers.length ? String(papers.length) : '—'} />
            <Stat label="时间范围" value={timeRange} />
            <Stat label="总被引次数" value={papers.length ? String(totalCitations) : '—'} />
            <Stat label="研究子领域" value={papers.length ? String(categories) : '—'} />
          </div>
          <button
            onClick={exportReport}
            disabled={!graphData}
            className="w-full flex items-center justify-center gap-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 text-sm font-medium py-2 rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Download size={16} />
            导出报告
          </button>
        </div>
      </div>
    </aside>
  );
}

function NavItem({
  icon,
  label,
  active = false,
  disabled = false,
  badge,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  disabled?: boolean;
  badge?: number;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={disabled ? '尚未启用' : undefined}
      className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-left transition-colors ${
        disabled
          ? 'cursor-not-allowed text-gray-300'
          : active
            ? 'text-[#6D4AFF] bg-gray-50 font-medium'
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
      }`}
    >
      <div className={active ? 'text-[#6D4AFF]' : 'text-gray-400'}>
        {icon}
      </div>
      <span className="flex-1">{label}</span>
      {typeof badge === 'number' && badge > 0 && (
        <span className="rounded-full bg-[#F2EFFF] px-2 py-0.5 text-[11px] font-semibold text-[#6D4AFF]">{badge}</span>
      )}
    </button>
  );
}

function Stat({ label, value }: { label: string, value: string }) {
  return (
    <div className="min-w-0">
      <div className="truncate whitespace-nowrap text-base font-semibold text-gray-900" title={value}>{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}
