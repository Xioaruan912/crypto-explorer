'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  Position,
  Handle
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { categoryColors } from '../constants/categories';
import { Paper } from '../types/paper';

const PaperNode = ({ data, selected }: { data: { paper: Paper, activeFilter?: string }, selected: boolean }) => {
  const paper = data.paper;
  if (!paper) return null;
  const color = categoryColors[paper.category] || categoryColors.foundation;
  
  const isFilteredOut = data.activeFilter && data.activeFilter !== 'all' && data.activeFilter !== paper.category;
  
  return (
    <div 
      className={`bg-white rounded-xl shadow-sm border-2 transition-all w-[240px] ${
        selected ? 'ring-4 ring-opacity-30 border-[#F97316]' : 'border-gray-200 hover:border-gray-300'
      } ${isFilteredOut ? 'opacity-30 grayscale' : 'opacity-100'}`}
      style={{ 
        borderColor: selected ? '#F97316' : color,
        boxShadow: selected ? `0 0 0 4px ${color}33` : '0 1px 2px 0 rgba(0, 0, 0, 0.05)' 
      }}
      title={`标题：${paper.titleZh} (${paper.titleEn})\n作者：${paper.authors.join(', ')}\n年份：${paper.year}\n会议：${paper.venue}\n被引次数：${paper.citations}`}
    >
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-gray-300" />
      <div className="p-3">
        <div className="text-xs font-semibold mb-1" style={{ color: isFilteredOut ? '#9ca3af' : color }}>{paper.venue}</div>
        <div className="font-bold text-sm text-gray-900 leading-tight mb-1 line-clamp-2">
          {paper.titleZh}
        </div>
        <div className="text-xs text-gray-500 mb-2 line-clamp-1" title={paper.titleEn}>
          {paper.titleEn}
        </div>
        <div className="text-xs text-gray-500 line-clamp-1">
          {paper.authors.join(', ')}
        </div>
      </div>
      {paper.category === 'foundation' && (
        <div className="bg-[#FFF7ED] px-3 py-1.5 border-t border-orange-100 text-xs font-medium text-[#F97316] rounded-b-[10px]">
          基础理论论文
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-gray-300" />
    </div>
  );
};

const nodeTypes = {
  paper: PaperNode,
};

interface ResearchMapProps {
  onNodeClick: (paperId: string) => void;
  activeFilter?: string;
  graphData?: { papers: Paper[], edges: { source: string, target: string }[] } | null;
}

import dagre from 'dagre';

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  
  // Nodes in our UI are roughly 240px wide and 120px tall
  const nodeWidth = 260;
  const nodeHeight = 140;

  dagreGraph.setGraph({ rankdir: direction, ranker: 'longest-path' });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = Position.Top;
    node.sourcePosition = Position.Bottom;

    // Shift to align center
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
  });

  return { nodes, edges };
};

export default function ResearchMap({ onNodeClick, activeFilter = 'all', graphData }: ResearchMapProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [direction, setDirection] = useState<'TB' | 'LR'>('TB');
  const [hideFiltered, setHideFiltered] = useState(false);

  useEffect(() => {
    if (!graphData || !graphData.papers) return;
    
    // Map backend papers to ReactFlow nodes
    const visiblePapers = hideFiltered && activeFilter !== 'all'
      ? graphData.papers.filter((paper) => paper.category === activeFilter)
      : graphData.papers;
    const visibleIds = new Set(visiblePapers.map((paper) => paper.id));
    const initialNodes: Node[] = visiblePapers.map(paper => ({
      id: paper.id,
      type: 'paper',
      position: { x: 0, y: 0 },
      data: { paper, activeFilter }
    }));
    
    // Map backend edges
    const initialEdges: Edge[] = graphData.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)).map(edge => ({
      id: `e-${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      animated: true,
      style: { strokeDasharray: '5,5' }
    }));

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      initialNodes,
      initialEdges,
      direction
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [graphData, activeFilter, direction, hideFiltered, setNodes, setEdges]);

  const onNodeClickInternal = useCallback((event: React.MouseEvent, node: Node) => {
    onNodeClick(node.id);
  }, [onNodeClick]);

  return (
    <div className="w-full h-[600px] bg-gray-50 border border-gray-200 rounded-xl overflow-hidden relative">
      <div className="absolute right-4 top-4 z-10 flex items-center gap-2 rounded-lg border border-gray-200 bg-white/95 p-1.5 text-xs shadow-sm backdrop-blur-sm">
        <button onClick={() => setDirection('TB')} className={`rounded-md px-2.5 py-1.5 ${direction === 'TB' ? 'bg-[#FFF7ED] text-[#F97316]' : 'text-gray-500 hover:bg-gray-50'}`}>纵向布局</button>
        <button onClick={() => setDirection('LR')} className={`rounded-md px-2.5 py-1.5 ${direction === 'LR' ? 'bg-[#FFF7ED] text-[#F97316]' : 'text-gray-500 hover:bg-gray-50'}`}>横向布局</button>
        <button onClick={() => setHideFiltered((value) => !value)} className={`rounded-md px-2.5 py-1.5 ${hideFiltered ? 'bg-[#FFF7ED] text-[#F97316]' : 'text-gray-500 hover:bg-gray-50'}`}>只显示筛选</button>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClickInternal}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-right"
        minZoom={0.2}
      >
        <Controls />
        <Background color="#ccc" gap={16} />
      </ReactFlow>
      
      <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur-sm p-3 rounded-lg border border-gray-200 shadow-sm flex items-center gap-4 text-xs font-medium">
        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-[#F97316]"></div>基础理论</div>
        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-[#FB923C]"></div>安全性</div>
        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-[#FDBA74]"></div>效率优化</div>
        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-[#EA580C]"></div>大规模 / 扩展性</div>
        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-[#C2410C]"></div>变体与扩展</div>
        <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-[#F59E0B]"></div>应用与实践</div>
      </div>
    </div>
  );
}
