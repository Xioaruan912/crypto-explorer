'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { categoryColors } from '../constants/categories';
import { Paper } from '../types/paper';
import { ResearchTimeRange } from '../types/research';

const categoryLabels: Record<string, string> = {
  foundation: '基础理论',
  security: '安全性',
  efficiency: '效率优化',
  scalability: '大规模 / 扩展性',
  variant: '变体与扩展',
  application: '应用与实践',
};

interface TooltipPayloadEntry {
  value: number;
  dataKey: string;
  fill: string;
}

interface TooltipProps {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-lg text-sm">
        <p className="font-bold mb-2 text-gray-900">{label} 年</p>
        {payload.map((entry: TooltipPayloadEntry, index: number) => (
          entry.value > 0 && (
            <div key={index} className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.fill }} />
              <span className="text-gray-600">{categoryLabels[entry.dataKey] || entry.dataKey}:</span>
              <span className="font-medium">{entry.value} 篇</span>
            </div>
          )
        ))}
      </div>
    );
  }
  return null;
};

interface ChartDataPoint {
  year: string;
  foundation: number;
  security: number;
  efficiency: number;
  scalability: number;
  variant: number;
  application: number;
}

export default function TimelineOverview({ activeFilter = 'all', papers = [], timeRange }: { activeFilter?: string, papers?: Paper[], timeRange?: ResearchTimeRange }) {
  const filteredPapers = activeFilter === 'all' 
    ? papers 
    : papers.filter(p => p.category === activeFilter);
    
  const totalPapers = filteredPapers.length;
  
  // Instead of useEffect we can compute it on the fly
  const yearMap: Record<number, Record<string, number>> = {};
  
  filteredPapers.forEach(p => {
    if (!yearMap[p.year]) {
      yearMap[p.year] = { 
        foundation: 0, 
        security: 0, 
        efficiency: 0, 
        scalability: 0, 
        variant: 0, 
        application: 0 
      };
    }
    if (yearMap[p.year][p.category] !== undefined) {
      yearMap[p.year][p.category] += 1;
    } else {
      yearMap[p.year][p.category] = 1;
    }
  });
  
  const sortedYears = Object.keys(yearMap).map(Number).sort((a, b) => a - b);
  
  const currentYear = new Date().getFullYear();
  const minYear = timeRange?.fromYear ?? (sortedYears.length > 0 ? sortedYears[0] : currentYear - 10);
  const maxYear = timeRange?.toYear ?? (sortedYears.length > 0 ? sortedYears[sortedYears.length - 1] : currentYear);
  
  const data: ChartDataPoint[] = [];
  for (let y = minYear; y <= maxYear; y++) {
    data.push({
      year: y.toString(),
      foundation: yearMap[y]?.foundation || 0,
      security: yearMap[y]?.security || 0,
      efficiency: yearMap[y]?.efficiency || 0,
      scalability: yearMap[y]?.scalability || 0,
      variant: yearMap[y]?.variant || 0,
      application: yearMap[y]?.application || 0,
    });
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 mt-6 shadow-sm">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="font-semibold text-gray-900">时间线概览</h3>
          <p className="text-xs text-gray-500 mt-1">按年份统计论文数量</p>
        </div>
        <div className="text-sm font-medium text-gray-500 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
          论文总数：<span className="text-[#6D4AFF]">{totalPapers} 篇</span>
        </div>
      </div>
      
      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 5, right: 0, left: -20, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis dataKey="year" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6B7280' }} />
            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6B7280' }} allowDecimals={false} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#F3F4F6' }} />
            <Bar dataKey="foundation" stackId="a" fill={categoryColors.foundation} radius={[0, 0, 4, 4]} />
            <Bar dataKey="security" stackId="a" fill={categoryColors.security} />
            <Bar dataKey="efficiency" stackId="a" fill={categoryColors.efficiency} />
            <Bar dataKey="scalability" stackId="a" fill={categoryColors.scalability} />
            <Bar dataKey="variant" stackId="a" fill={categoryColors.variant} />
            <Bar dataKey="application" stackId="a" fill={categoryColors.application} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
