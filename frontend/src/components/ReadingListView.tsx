'use client';

import { useState } from 'react';
import { BookOpenCheck, Trash2 } from 'lucide-react';
import { ReadingListItem, ReadingStatus } from '../types/research';

const statusLabel: Record<ReadingStatus, string> = { to_read: '待读', reading: '在读', done: '已读' };

export default function ReadingListView({
  items,
  onUpdate,
  onRemove,
  onSelect,
}: {
  items: ReadingListItem[];
  onUpdate: (paperId: string, patch: Partial<{ status: ReadingStatus; priority: 1 | 2 | 3; note: string }>) => void;
  onRemove: (paperId: string) => void;
  onSelect: (paperId: string) => void;
}) {
  const [filter, setFilter] = useState<'all' | ReadingStatus>('all');
  const filteredItems = filter === 'all' ? items : items.filter((item) => item.status === filter);
  const counts = {
    to_read: items.filter((item) => item.status === 'to_read').length,
    reading: items.filter((item) => item.status === 'reading').length,
    done: items.filter((item) => item.status === 'done').length,
  };

  return (
    <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">阅读清单</h2>
          <p className="mt-1 text-sm text-gray-500">持久化管理待读、在读、已读论文和阅读备注。</p>
        </div>
        <div className="rounded-lg bg-[#F2EFFF] px-3 py-2 text-sm font-medium text-[#6D4AFF]">{items.length} 篇</div>
      </div>
      <div className="mb-5 flex gap-2 rounded-xl bg-gray-50 p-1.5">
        {([
          ['all', `全部 ${items.length}`],
          ['to_read', `待读 ${counts.to_read}`],
          ['reading', `在读 ${counts.reading}`],
          ['done', `已读 ${counts.done}`],
        ] as const).map(([value, label]) => (
          <button key={value} onClick={() => setFilter(value)} className={`rounded-lg px-3 py-1.5 text-sm ${filter === value ? 'bg-white font-medium text-[#6D4AFF] shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>{label}</button>
        ))}
      </div>
      {items.length === 0 ? (
        <div className="flex h-72 flex-col items-center justify-center text-center text-gray-400">
          <BookOpenCheck className="mb-3 h-10 w-10" />
          <div className="font-medium text-gray-500">阅读清单还是空的</div>
          <div className="mt-1 text-sm">在论文详情里点击“加入阅读清单”。</div>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredItems.map((item) => (
            <div key={item.paper.id} className="rounded-xl border border-gray-100 bg-gray-50/70 p-4">
              <div className="flex gap-4">
                <button onClick={() => onSelect(item.paper.id)} className="min-w-0 flex-1 text-left">
                  <div className="font-medium text-gray-900 hover:text-[#6D4AFF]">{item.paper.titleEn}</div>
                  <div className="mt-1 text-sm text-gray-500">{item.paper.authors.join(', ')} · {item.paper.year}</div>
                </button>
                <select
                  value={item.status}
                  onChange={(e) => onUpdate(item.paper.id, { status: e.target.value as ReadingStatus })}
                  className="h-9 rounded-lg border border-gray-200 bg-white px-2 text-sm text-gray-600"
                >
                  {Object.entries(statusLabel).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <select
                  value={item.priority}
                  onChange={(e) => onUpdate(item.paper.id, { priority: Number(e.target.value) as 1 | 2 | 3 })}
                  className="h-9 rounded-lg border border-gray-200 bg-white px-2 text-sm text-gray-600"
                >
                  <option value={1}>高优先</option>
                  <option value={2}>中优先</option>
                  <option value={3}>低优先</option>
                </select>
                <button onClick={() => onRemove(item.paper.id)} className="h-9 rounded-lg border border-gray-200 bg-white px-3 text-gray-400 hover:text-red-500" title="移除">
                  <Trash2 size={16} />
                </button>
              </div>
              <textarea
                key={`${item.paper.id}-${item.updated_at}`}
                defaultValue={item.note}
                onBlur={(e) => {
                  if (e.target.value !== item.note) onUpdate(item.paper.id, { note: e.target.value });
                }}
                placeholder="记录阅读目标、关键结论、待验证问题……"
                className="mt-3 min-h-20 w-full resize-y rounded-lg border border-gray-200 bg-white p-3 text-sm text-gray-700 outline-none focus:border-[#9D87FF]"
              />
            </div>
          ))}
          {filteredItems.length === 0 && items.length > 0 && (
            <div className="py-16 text-center text-sm text-gray-400">这个阅读状态下还没有论文。</div>
          )}
        </div>
      )}
    </div>
  );
}
