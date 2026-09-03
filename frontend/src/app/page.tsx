'use client';

import React, { useEffect, useState } from 'react';
import AppHeader from '@/components/AppHeader';
import Sidebar from '@/components/Sidebar';
import ResearchFilters from '@/components/ResearchFilters';
import ResearchMap from '@/components/ResearchMap';
import TimelineOverview from '@/components/TimelineOverview';
import TimelineView from '@/components/TimelineView';
import CitationNetworkView from '@/components/CitationNetworkView';
import ReadingListView from '@/components/ReadingListView';
import PaperDetailsPanel from '@/components/PaperDetailsPanel';
import WorkspaceView from '@/components/WorkspaceView';
import DiscoveryView from '@/components/DiscoveryView';
import { Network, BarChart3, Loader2, AlertCircle, Search, GitMerge, BookOpen } from 'lucide-react';
import { paperService, GraphData } from '@/services/paperService';
import { researchService } from '@/services/researchService';
import { FavoriteItem, ReadingListItem, ReadingStatus, ResearchTimeRange, ResearchView, WorkspaceSection } from '@/types/research';
import { Paper } from '@/types/paper';

export default function Home() {
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ResearchView>('graph');
  const [workspace, setWorkspace] = useState<WorkspaceSection | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [currentTopic, setCurrentTopic] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');
  const [researchTimeRange, setResearchTimeRange] = useState<ResearchTimeRange>({ strategy: 'relevance' });
  const [error, setError] = useState<string | null>(null);

  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [readingList, setReadingList] = useState<ReadingListItem[]>([]);
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [discoverySelectedPaper, setDiscoverySelectedPaper] = useState<Paper | null>(null);

  useEffect(() => {
    researchService.listReading().then(setReadingList).catch((e) => console.error(e));
    researchService.listFavorites().then(setFavorites).catch((e) => console.error(e));
  }, []);

  const switchResearchView = (mode: ResearchView) => {
    setWorkspace(null);
    setViewMode(mode);
    setSelectedPaperId(null);
    setDiscoverySelectedPaper(null);
  };

  const openWorkspace = (section: WorkspaceSection) => {
    setWorkspace(section);
    if (section === 'favorites') {
      if (!selectedPaperId || !favorites.some((item) => item.paper.id === selectedPaperId)) {
        setSelectedPaperId(null);
      }
    } else {
      setSelectedPaperId(null);
    }
  };

  const addReading = async (paper: Paper) => {
    try {
      const item = await researchService.addReading(paper);
      setReadingList((current) => [item, ...current.filter((entry) => entry.paper.id !== paper.id)]);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加入阅读清单失败');
    }
  };

  const updateReading = async (
    paperId: string,
    patch: Partial<{ status: ReadingStatus; priority: 1 | 2 | 3; note: string }>,
  ) => {
    setReadingList((current) => current.map((item) => item.paper.id === paperId ? { ...item, ...patch } : item));
    try {
      const updated = await researchService.updateReading(paperId, patch);
      setReadingList((current) => current.map((item) => item.paper.id === paperId ? updated : item));
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新阅读清单失败');
      researchService.listReading().then(setReadingList).catch(() => undefined);
    }
  };

  const removeReading = async (paperId: string) => {
    try {
      await researchService.removeReading(paperId);
      setReadingList((current) => current.filter((item) => item.paper.id !== paperId));
    } catch (e) {
      setError(e instanceof Error ? e.message : '移除阅读清单失败');
    }
  };

  const selectFromReading = (paperId: string) => {
    setSelectedPaperId(paperId);
  };

  const toggleFavorite = async (paper: Paper) => {
    const exists = favorites.some((item) => item.paper.id === paper.id);
    try {
      if (exists) {
        await researchService.removeFavorite(paper.id);
        setFavorites((current) => current.filter((item) => item.paper.id !== paper.id));
      } else {
        const item = await researchService.addFavorite(paper);
        setFavorites((current) => [item, ...current.filter((entry) => entry.paper.id !== paper.id)]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新收藏失败');
    }
  };

  const removeFavorite = async (paperId: string) => {
    try {
      await researchService.removeFavorite(paperId);
      setFavorites((current) => current.filter((item) => item.paper.id !== paperId));
      if (selectedPaperId === paperId) setSelectedPaperId(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : '取消收藏失败');
    }
  };

  const handleSearch = async (query: string, range: ResearchTimeRange = researchTimeRange) => {
    setWorkspace(null);
    setIsSearching(true);
    setError(null);
    setCurrentTopic(query);
    setSelectedPaperId(null);
    setDiscoverySelectedPaper(null);
    try {
      const data = await paperService.searchGraph(query, range);
      setGraphData(data);
      if (data.papers.length > 0) {
        // Find foundation or highest cited to select initially
        const foundation = data.papers.find(p => p.category === 'foundation') || data.papers[0];
        setSelectedPaperId(foundation.id);
      }
    } catch (e) {
      console.error(e);
      setGraphData(null);
      setError(e instanceof Error ? e.message : '搜索失败，请稍后重试');
    } finally {
      setIsSearching(false);
    }
  };

  const applyResearchTimeRange = (range: ResearchTimeRange) => {
    setResearchTimeRange(range);
    if (currentTopic) void handleSearch(currentTopic, range);
  };

  const researchTimeRangeLabel = researchTimeRange.fromYear || researchTimeRange.toYear
    ? `${researchTimeRange.fromYear || '最早'}–${researchTimeRange.toYear || new Date().getFullYear()}`
    : '全部年份';

  const selectDiscoveryPaper = (paper: Paper) => {
    setDiscoverySelectedPaper(paper);
    setSelectedPaperId(paper.id);
  };

  const currentSelectedPaper = selectedPaperId
    ? (discoverySelectedPaper?.id === selectedPaperId ? discoverySelectedPaper : null)
      || graphData?.papers.find(x => x.id === selectedPaperId)
      || readingList.find((item) => item.paper.id === selectedPaperId)?.paper
      || favorites.find((item) => item.paper.id === selectedPaperId)?.paper
      || null
    : null;

  const discoveryMode = viewMode === 'papers' || viewMode === 'authors' || viewMode === 'venues'
    ? viewMode
    : null;

  return (
    <div className="flex flex-col h-screen bg-[#F8F9FC] text-[#171717] overflow-hidden">
      <AppHeader onSearch={handleSearch} activeWorkspace={workspace} onWorkspaceChange={openWorkspace} />
      
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          graphData={graphData}
          viewMode={viewMode}
          readingCount={readingList.length}
          favoriteCount={favorites.length}
          activeWorkspace={workspace}
          timeRangeLabel={researchTimeRangeLabel}
          onViewModeChange={switchResearchView}
          onWorkspaceChange={openWorkspace}
        />
        
        <main className="relative flex h-full min-w-0 flex-1 flex-col overflow-y-auto overflow-x-hidden">
          {isSearching && (
            <div className="absolute inset-0 z-50 bg-white/70 backdrop-blur-sm flex flex-col items-center justify-center">
              <Loader2 className="w-10 h-10 text-[#6D4AFF] animate-spin mb-4" />
              <p className="text-gray-700 font-medium text-lg">正在分析文献网络并生成图谱...</p>
              <p className="text-gray-500 text-sm mt-2">主题: {currentTopic}</p>
            </div>
          )}
          
          <div className="p-8 max-w-6xl mx-auto w-full">
            {error && (
              <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <div className="font-medium">操作出现问题</div>
                  <div className="mt-0.5 text-red-600">{error}</div>
                </div>
              </div>
            )}

            {workspace ? (
              <WorkspaceView
                section={workspace}
                favorites={favorites}
                onRunSearch={handleSearch}
                onSelectFavorite={setSelectedPaperId}
                onRemoveFavorite={removeFavorite}
                onBack={() => setWorkspace(null)}
              />
            ) : discoveryMode ? (
              <DiscoveryView
                mode={discoveryMode}
                favoriteIds={new Set(favorites.map((item) => item.paper.id))}
                readingIds={new Set(readingList.map((item) => item.paper.id))}
                onSelectPaper={selectDiscoveryPaper}
                onToggleFavorite={toggleFavorite}
                onAddReading={addReading}
              />
            ) : <>
            <div className="flex items-start justify-between mb-2">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 mb-1">
                  {viewMode === 'graph' && '研究图谱'}
                  {viewMode === 'timeline' && '研究时间线'}
                  {viewMode === 'citations' && '引文网络'}
                  {viewMode === 'reading' && '阅读清单'}
                </h1>
                <p className="text-gray-500 text-sm">
                  {viewMode === 'reading'
                    ? '管理你的阅读队列、阅读进度、优先级和研究备注'
                    : currentTopic ? `可视化 ${currentTopic} 领域的研究演化` : '输入密码学主题或论文名称开始探索'}
                </p>
              </div>
              
              <div className="flex bg-gray-100 p-1 rounded-lg border border-gray-200">
                <button 
                  onClick={() => switchResearchView('graph')}
                  className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    viewMode === 'graph' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <Network size={16} />
                  图谱视图
                </button>
                <button 
                  onClick={() => switchResearchView('timeline')}
                  className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    viewMode === 'timeline' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <BarChart3 size={16} />
                  时间线视图
                </button>
                <button
                  onClick={() => switchResearchView('citations')}
                  className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${viewMode === 'citations' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                >
                  <GitMerge size={16} /> 引文网络
                </button>
                <button
                  onClick={() => switchResearchView('reading')}
                  className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${viewMode === 'reading' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                >
                  <BookOpen size={16} /> 阅读清单
                </button>
              </div>
            </div>

            {viewMode !== 'reading' && (
              <ResearchFilters
                activeFilter={activeFilter}
                onFilterChange={setActiveFilter}
                timeRange={researchTimeRange}
                onTimeRangeChange={applyResearchTimeRange}
              />
            )}
            
            {viewMode === 'reading' ? (
              <ReadingListView items={readingList} onUpdate={updateReading} onRemove={removeReading} onSelect={selectFromReading} />
            ) : !graphData && !isSearching ? (
              <div className="mt-6 flex h-[600px] w-full flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white text-center">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#F2EFFF] text-[#6D4AFF]">
                  <Search size={26} />
                </div>
                <h2 className="text-lg font-semibold text-gray-900">等待你的搜索</h2>
                <p className="mt-2 max-w-md text-sm leading-6 text-gray-500">
                  在顶部输入密码学主题、论文标题或关键词。系统不会自动发起默认查询。
                </p>
              </div>
            ) : viewMode === 'graph' ? (
              <ResearchMap 
                onNodeClick={(id) => setSelectedPaperId(id)} 
                activeFilter={activeFilter} 
                graphData={graphData}
              />
            ) : viewMode === 'timeline' && graphData ? (
              <TimelineView papers={graphData.papers} activeFilter={activeFilter} onSelect={setSelectedPaperId} />
            ) : viewMode === 'citations' && graphData ? (
              <CitationNetworkView graphData={graphData} selectedPaperId={selectedPaperId} onSelect={setSelectedPaperId} />
            ) : null}
            
            {graphData && viewMode === 'graph' && <TimelineOverview activeFilter={activeFilter} papers={graphData.papers} timeRange={researchTimeRange} />}
            </>}
          </div>
        </main>

        {(!workspace || workspace === 'favorites') && (
          <PaperDetailsPanel
            key={currentSelectedPaper?.id || 'empty'}
            paper={currentSelectedPaper}
            inReadingList={Boolean(currentSelectedPaper && readingList.some((item) => item.paper.id === currentSelectedPaper.id))}
            isFavorite={Boolean(currentSelectedPaper && favorites.some((item) => item.paper.id === currentSelectedPaper.id))}
            onAddReading={addReading}
            onToggleFavorite={toggleFavorite}
          />
        )}
      </div>
    </div>
  );
}
