'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  BookOpenCheck,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Circle,
  ListChecks,
  Plus,
  Trash2,
} from 'lucide-react';
import { researchService } from '../services/researchService';
import {
  ReadingListItem,
  ReadingStatus,
  ReadingTask,
  ReadingTaskStatus,
  ReadingTaskType,
} from '../types/research';
import { addDays, formatWeekRange, getWeekDays, startOfWeek } from '../utils/week';

const statusLabel: Record<ReadingStatus, string> = { to_read: '待读', reading: '在读', done: '已读' };
const taskStatusLabel: Record<ReadingTaskStatus, string> = { todo: '待完成', doing: '进行中', done: '已完成' };
const taskTypeLabel: Record<ReadingTaskType, string> = {
  read: '阅读',
  notes: '笔记',
  review: '复习',
  reproduce: '复现',
  custom: '其他',
};
const taskTypeDefaultText: Record<ReadingTaskType, string> = {
  read: '阅读论文',
  notes: '整理 Markdown 阅读笔记',
  review: '复习论文与关键结论',
  reproduce: '复现 / 验证论文内容',
  custom: '研究任务',
};

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
  const [mode, setMode] = useState<'week' | 'library'>('week');
  const [filter, setFilter] = useState<'all' | ReadingStatus>('all');
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const [tasks, setTasks] = useState<ReadingTask[]>([]);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [taskError, setTaskError] = useState('');
  const [draftPaperId, setDraftPaperId] = useState('');
  const [draftDayIndex, setDraftDayIndex] = useState(() => Math.min((new Date().getDay() + 6) % 7, 6));
  const [draftType, setDraftType] = useState<ReadingTaskType>('read');
  const [draftText, setDraftText] = useState(taskTypeDefaultText.read);
  const [addingTask, setAddingTask] = useState(false);

  const weekDays = useMemo(() => getWeekDays(weekStart), [weekStart]);
  const weekStartIso = weekDays[0].iso;
  const weekEndIso = weekDays[6].iso;
  const selectedDraftPaperId = draftPaperId || items[0]?.paper.id || '';

  useEffect(() => {
    let active = true;
    researchService.listReadingTasks(weekStartIso, weekEndIso)
      .then((data) => { if (active) setTasks(data); })
      .catch((error) => { if (active) setTaskError(error instanceof Error ? error.message : '本周计划加载失败'); })
      .finally(() => { if (active) setTasksLoading(false); });
    return () => { active = false; };
  }, [weekEndIso, weekStartIso]);

  const navigateWeek = (days: number) => {
    setTasksLoading(true);
    setTaskError('');
    setTasks([]);
    setWeekStart((current) => addDays(current, days));
  };

  const goThisWeek = () => {
    setTasksLoading(true);
    setTaskError('');
    setTasks([]);
    setWeekStart(startOfWeek(new Date()));
  };

  const addTask = async () => {
    if (!selectedDraftPaperId || !draftText.trim()) return;
    setAddingTask(true);
    setTaskError('');
    try {
      const created = await researchService.createReadingTask({
        paperId: selectedDraftPaperId,
        scheduledDate: weekDays[draftDayIndex].iso,
        taskType: draftType,
        taskText: draftText.trim(),
      });
      setTasks((current) => [...current, created].sort(sortTasks));
    } catch (error) {
      setTaskError(error instanceof Error ? error.message : '创建任务失败');
    } finally {
      setAddingTask(false);
    }
  };

  const patchTask = async (
    taskId: number,
    patch: Partial<{
      scheduled_date: string;
      task_type: ReadingTaskType;
      task_text: string;
      status: ReadingTaskStatus;
    }>,
  ) => {
    setTaskError('');
    try {
      const updated = await researchService.updateReadingTask(taskId, patch);
      setTasks((current) => current.map((task) => task.id === taskId ? updated : task).sort(sortTasks));
    } catch (error) {
      setTaskError(error instanceof Error ? error.message : '更新任务失败');
    }
  };

  const removeTask = async (taskId: number) => {
    try {
      await researchService.removeReadingTask(taskId);
      setTasks((current) => current.filter((task) => task.id !== taskId));
    } catch (error) {
      setTaskError(error instanceof Error ? error.message : '删除任务失败');
    }
  };

  const filteredItems = filter === 'all' ? items : items.filter((item) => item.status === filter);
  const counts = {
    to_read: items.filter((item) => item.status === 'to_read').length,
    reading: items.filter((item) => item.status === 'reading').length,
    done: items.filter((item) => item.status === 'done').length,
  };
  const doneTasks = tasks.filter((task) => task.status === 'done').length;
  const scheduledPaperIds = new Set(tasks.map((task) => task.paper.id));
  const unscheduledCount = items.filter((item) => !scheduledPaperIds.has(item.paper.id) && item.status !== 'done').length;

  return (
    <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">阅读清单</h2>
          <p className="mt-1 text-sm text-gray-500">把阅读清单排成一周 TODO：哪天读什么、做笔记还是复现，都可以单独安排。</p>
        </div>
        <div className="flex items-center rounded-lg bg-gray-100 p-1">
          <button onClick={() => setMode('week')} className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm ${mode === 'week' ? 'bg-white font-medium text-[#6D4AFF] shadow-sm' : 'text-gray-500'}`}><CalendarDays size={15} />本周计划</button>
          <button onClick={() => setMode('library')} className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm ${mode === 'library' ? 'bg-white font-medium text-[#6D4AFF] shadow-sm' : 'text-gray-500'}`}><ListChecks size={15} />阅读库</button>
        </div>
      </div>

      {mode === 'week' ? (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-200 bg-gray-50/70 p-3">
            <div className="flex items-center gap-2">
              <button onClick={() => navigateWeek(-7)} className="rounded-lg border border-gray-200 bg-white p-2 text-gray-500 hover:text-[#6D4AFF]" title="上一周"><ChevronLeft size={16} /></button>
              <button onClick={goThisWeek} className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 hover:text-[#6D4AFF]">本周</button>
              <button onClick={() => navigateWeek(7)} className="rounded-lg border border-gray-200 bg-white p-2 text-gray-500 hover:text-[#6D4AFF]" title="下一周"><ChevronRight size={16} /></button>
              <div className="ml-2 text-sm font-semibold text-gray-900">{formatWeekRange(weekStart)}</div>
            </div>
            <div className="flex gap-2 text-xs">
              <span className="rounded-full bg-[#F2EFFF] px-3 py-1.5 font-medium text-[#6D4AFF]">{doneTasks}/{tasks.length} 已完成</span>
              {unscheduledCount > 0 && <span className="rounded-full bg-amber-50 px-3 py-1.5 font-medium text-amber-700">{unscheduledCount} 篇待读未安排</span>}
            </div>
          </div>

          <div className="grid gap-2 rounded-xl border border-[#DDD5FF] bg-[#FAF9FF] p-3 lg:grid-cols-[minmax(180px,1.35fr)_110px_130px_minmax(220px,1.6fr)_90px]">
            <select value={selectedDraftPaperId} onChange={(event) => setDraftPaperId(event.target.value)} disabled={!items.length} className="min-w-0 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:border-[#9D87FF]">
              {items.length ? items.map((item) => <option key={item.paper.id} value={item.paper.id}>{item.paper.titleEn}</option>) : <option value="">先加入论文到阅读清单</option>}
            </select>
            <select value={draftDayIndex} onChange={(event) => setDraftDayIndex(Number(event.target.value))} className="rounded-lg border border-gray-200 bg-white px-2 py-2 text-sm text-gray-700">
              {weekDays.map((day, index) => <option key={day.iso} value={index}>{day.weekday} {day.shortDate}</option>)}
            </select>
            <select value={draftType} onChange={(event) => { const next = event.target.value as ReadingTaskType; setDraftType(next); setDraftText(taskTypeDefaultText[next]); }} className="rounded-lg border border-gray-200 bg-white px-2 py-2 text-sm text-gray-700">
              {Object.entries(taskTypeLabel).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <input value={draftText} onChange={(event) => setDraftText(event.target.value)} placeholder="这一天具体要做什么？" className="min-w-0 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:border-[#9D87FF]" />
            <button disabled={!items.length || addingTask || !draftText.trim()} onClick={addTask} className="flex items-center justify-center gap-1 rounded-lg bg-[#6D4AFF] px-3 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-40"><Plus size={15} />安排</button>
          </div>

          {taskError && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{taskError}</div>}

          {tasksLoading ? (
            <div className="flex h-48 items-center justify-center text-sm text-gray-400">正在加载本周计划...</div>
          ) : (
            <div className="overflow-x-auto pb-2">
              <div className="grid min-w-[1050px] grid-cols-7 gap-3">
                {weekDays.map((day) => {
                  const dayTasks = tasks.filter((task) => task.scheduled_date === day.iso);
                  return (
                    <section key={day.iso} className={`min-h-[300px] rounded-xl border p-3 ${day.isToday ? 'border-[#9D87FF] bg-[#FAF9FF]' : 'border-gray-200 bg-gray-50/60'}`}>
                      <div className="mb-3 flex items-start justify-between">
                        <div><div className={`text-sm font-semibold ${day.isToday ? 'text-[#6D4AFF]' : 'text-gray-800'}`}>{day.weekday}</div><div className="mt-0.5 text-xs text-gray-400">{day.shortDate}</div></div>
                        <span className="rounded-full bg-white px-2 py-1 text-[11px] text-gray-500">{dayTasks.length}</span>
                      </div>
                      <div className="space-y-2">
                        {dayTasks.map((task) => (
                          <div key={task.id} className={`rounded-lg border bg-white p-2.5 shadow-sm ${task.status === 'done' ? 'border-emerald-100 opacity-65' : task.status === 'doing' ? 'border-amber-200' : 'border-gray-200'}`}>
                            <div className="flex items-start gap-2">
                              <button onClick={() => patchTask(task.id, { status: task.status === 'done' ? 'todo' : 'done' })} className={`mt-0.5 shrink-0 ${task.status === 'done' ? 'text-emerald-500' : 'text-gray-300 hover:text-[#6D4AFF]'}`} title={task.status === 'done' ? '标记未完成' : '标记完成'}>{task.status === 'done' ? <CheckCircle2 size={16} /> : <Circle size={16} />}</button>
                              <button onClick={() => onSelect(task.paper.id)} className="min-w-0 flex-1 text-left">
                                <div className="line-clamp-2 text-xs font-semibold leading-5 text-gray-900 hover:text-[#6D4AFF]">{task.paper.titleEn}</div>
                              </button>
                            </div>
                            <textarea
                              key={`${task.id}-${task.updated_at}`}
                              defaultValue={task.task_text}
                              rows={2}
                              onBlur={(event) => {
                                const value = event.target.value.trim();
                                if (value && value !== task.task_text) patchTask(task.id, { task_text: value });
                              }}
                              className="mt-2 w-full resize-none rounded-md border border-transparent bg-gray-50 px-2 py-1.5 text-xs leading-5 text-gray-600 outline-none focus:border-[#D8CEFF] focus:bg-white"
                            />
                            <div className="mt-2 flex items-center justify-between gap-1">
                              <select value={task.task_type} onChange={(event) => patchTask(task.id, { task_type: event.target.value as ReadingTaskType })} className="max-w-[90px] rounded border border-[#E4DEFF] bg-[#F8F6FF] px-1 py-1 text-[10px] font-medium text-[#6D4AFF]">
                                {Object.entries(taskTypeLabel).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                              </select>
                              <button onClick={() => removeTask(task.id)} className="p-1 text-gray-300 hover:text-red-500" title="删除任务"><Trash2 size={13} /></button>
                            </div>
                            <div className="mt-2 grid grid-cols-2 gap-1">
                              <select value={task.status} onChange={(event) => patchTask(task.id, { status: event.target.value as ReadingTaskStatus })} className="min-w-0 rounded border border-gray-100 bg-white px-1 py-1 text-[10px] text-gray-500">
                                {Object.entries(taskStatusLabel).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                              </select>
                              <select value={task.scheduled_date} onChange={(event) => patchTask(task.id, { scheduled_date: event.target.value })} className="min-w-0 rounded border border-gray-100 bg-white px-1 py-1 text-[10px] text-gray-500">
                                {weekDays.map((targetDay) => <option key={targetDay.iso} value={targetDay.iso}>{targetDay.weekday}</option>)}
                              </select>
                            </div>
                          </div>
                        ))}
                        {!dayTasks.length && <div className="rounded-lg border border-dashed border-gray-200 py-8 text-center text-[11px] text-gray-300">暂无任务</div>}
                      </div>
                    </section>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div>
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
                      <div className="line-clamp-2 font-medium text-gray-900 hover:text-[#6D4AFF]">{item.paper.titleEn}</div>
                      <div className="mt-1 truncate text-sm text-gray-500">{item.paper.authors.join(', ')} · {item.paper.year}</div>
                    </button>
                    <select value={item.status} onChange={(event) => onUpdate(item.paper.id, { status: event.target.value as ReadingStatus })} className="h-9 rounded-lg border border-gray-200 bg-white px-2 text-sm text-gray-600">
                      {Object.entries(statusLabel).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                    </select>
                    <select value={item.priority} onChange={(event) => onUpdate(item.paper.id, { priority: Number(event.target.value) as 1 | 2 | 3 })} className="h-9 rounded-lg border border-gray-200 bg-white px-2 text-sm text-gray-600">
                      <option value={1}>高优先</option><option value={2}>中优先</option><option value={3}>低优先</option>
                    </select>
                    <button onClick={() => { onRemove(item.paper.id); setTasks((current) => current.filter((task) => task.paper.id !== item.paper.id)); }} className="h-9 rounded-lg border border-gray-200 bg-white px-3 text-gray-400 hover:text-red-500" title="移除"><Trash2 size={16} /></button>
                  </div>
                  <textarea key={`${item.paper.id}-${item.updated_at}`} defaultValue={item.note} onBlur={(event) => { if (event.target.value !== item.note) onUpdate(item.paper.id, { note: event.target.value }); }} placeholder="记录阅读目标、关键结论、待验证问题……" className="mt-3 min-h-20 w-full resize-y rounded-lg border border-gray-200 bg-white p-3 text-sm text-gray-700 outline-none focus:border-[#9D87FF]" />
                </div>
              ))}
              {filteredItems.length === 0 && items.length > 0 && <div className="py-16 text-center text-sm text-gray-400">这个阅读状态下还没有论文。</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function sortTasks(a: ReadingTask, b: ReadingTask) {
  return a.scheduled_date.localeCompare(b.scheduled_date) || a.id - b.id;
}
