import React, { useState } from 'react';
import { Search, HelpCircle, LayoutDashboard, History, Bookmark, User, Share2 } from 'lucide-react';
import { WorkspaceSection } from '../types/research';

interface AppHeaderProps {
  onSearch?: (query: string) => void;
  activeWorkspace?: WorkspaceSection | null;
  onWorkspaceChange?: (section: WorkspaceSection) => void;
}

export default function AppHeader({ onSearch, activeWorkspace, onWorkspaceChange }: AppHeaderProps) {
  const [query, setQuery] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch && query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 flex items-center justify-center text-[#6D4AFF]">
          <Share2 size={24} strokeWidth={2.5} />
        </div>
        <span className="font-semibold text-lg text-gray-900 tracking-tight">密码学研究图谱</span>
      </div>

      <div className="flex-1 max-w-2xl px-8 flex items-center">
        <form onSubmit={handleSearch} className="relative w-full flex items-center">
          <div className="absolute left-3 text-gray-400">
            <Search size={18} />
          </div>
          <input 
            type="text" 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索密码学主题、论文、作者或会议"
            className="w-full pl-10 pr-24 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6D4AFF] focus:border-transparent transition-all"
          />
          <button type="submit" className="absolute right-1.5 px-4 py-1.5 bg-[#6D4AFF] hover:bg-purple-700 text-white text-sm font-medium rounded-md transition-colors">
            搜索
          </button>
        </form>
      </div>

      <div className="flex items-center gap-5 text-gray-500">
        <button onClick={() => onWorkspaceChange?.('help')} className={`flex items-center gap-2 transition-colors text-sm ${activeWorkspace === 'help' ? 'text-[#6D4AFF] font-medium' : 'hover:text-gray-900'}`}>
          <HelpCircle size={18} />
          <span>帮助</span>
        </button>
        <button onClick={() => onWorkspaceChange?.('dashboard')} className={`flex items-center gap-2 transition-colors text-sm ${activeWorkspace === 'dashboard' ? 'text-[#6D4AFF] font-medium' : 'hover:text-gray-900'}`}>
          <LayoutDashboard size={18} />
          <span>仪表盘</span>
        </button>
        <button onClick={() => onWorkspaceChange?.('history')} className={`flex items-center gap-2 transition-colors text-sm ${activeWorkspace === 'history' ? 'text-[#6D4AFF] font-medium' : 'hover:text-gray-900'}`}>
          <History size={18} />
          <span>历史记录</span>
        </button>
        <button onClick={() => onWorkspaceChange?.('favorites')} className={`flex items-center gap-2 transition-colors text-sm ${activeWorkspace === 'favorites' ? 'text-[#6D4AFF] font-medium' : 'hover:text-gray-900'}`}>
          <Bookmark size={18} />
          <span>我的收藏</span>
        </button>
        <button onClick={() => onWorkspaceChange?.('profile')} className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${activeWorkspace === 'profile' ? 'bg-[#F2EFFF] text-[#6D4AFF] ring-1 ring-[#D8CEFF]' : 'bg-gray-100 hover:bg-gray-200'}`} title="个人中心">
          <User size={18} />
        </button>
      </div>
    </header>
  );
}
