'use client';

import React, { useEffect, useState } from 'react';
import {
  ArrowRight,
  Bookmark,
  BookOpenCheck,
  CalendarDays,
  CheckCircle2,
  Circle,
  Clock3,
  FileSearch,
  HelpCircle,
  History,
  LayoutDashboard,
  Loader2,
  Download,
  DatabaseBackup,
  KeyRound,
  LogOut,
  PenTool,
  Save,
  Search,
  Trash2,
  Upload,
  User,
} from 'lucide-react';
import { researchService } from '@/services/researchService';
import { authService } from '@/services/authService';
import {
  AccountInfo,
  DashboardData,
  FavoriteItem,
  NoteItem,
  ReadingTask,
  SearchHistoryItem,
  UserProfile,
  WorkspaceSection,
} from '@/types/research';
import { getWeekDays, startOfWeek } from '@/utils/week';

interface WorkspaceViewProps {
  section: WorkspaceSection;
  favorites: FavoriteItem[];
  onRunSearch: (query: string) => void;
  onSelectFavorite: (paperId: string) => void;
  onRemoveFavorite: (paperId: string) => void;
  onOpenReadingList: () => void;
  onBack: () => void;
}

const sectionMeta: Record<WorkspaceSection, { title: string; subtitle: string; icon: React.ReactNode }> = {
  help: { title: '帮助中心', subtitle: '快速了解密码学研究图谱的主要工作流', icon: <HelpCircle size={20} /> },
  dashboard: { title: '研究仪表盘', subtitle: '优先查看本周阅读 TODO，再汇总搜索、阅读、收藏与笔记活动', icon: <LayoutDashboard size={20} /> },
  history: { title: '历史记录', subtitle: '查看过去的研究搜索并快速重新探索', icon: <History size={20} /> },
  favorites: { title: '我的收藏', subtitle: '集中管理你标记的重要论文', icon: <Bookmark size={20} /> },
  profile: { title: '个人中心', subtitle: '维护研究者资料与研究方向', icon: <User size={20} /> },
  notes: { title: 'Markdown 笔记', subtitle: '集中管理与论文关联的本地 Markdown 阅读笔记', icon: <PenTool size={20} /> },
  account: { title: '账户管理', subtitle: '修改登录凭据、管理会话并导入/导出研究数据备份', icon: <User size={20} /> },
};

export default function WorkspaceView({ section, favorites, onRunSearch, onSelectFavorite, onRemoveFavorite, onOpenReadingList, onBack }: WorkspaceViewProps) {
  const meta = sectionMeta[section];
  return (
    <div className="w-full">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-[#6D4AFF]">{meta.icon}<span className="text-sm font-semibold">研究工作区</span></div>
          <h1 className="text-2xl font-bold text-gray-900">{meta.title}</h1>
          <p className="mt-1 text-sm text-gray-500">{meta.subtitle}</p>
        </div>
        <button onClick={onBack} className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50">返回研究图谱</button>
      </div>
      {section === 'help' && <HelpView />}
      {section === 'dashboard' && <DashboardView onRunSearch={onRunSearch} onOpenReadingList={onOpenReadingList} />}
      {section === 'history' && <HistoryView onRunSearch={onRunSearch} />}
      {section === 'favorites' && <FavoritesView favorites={favorites} onSelect={onSelectFavorite} onRemove={onRemoveFavorite} />}
      {section === 'profile' && <ProfileView />}
      {section === 'notes' && <NotesView />}
      {section === 'account' && <AccountView />}
    </div>
  );
}

function HelpView() {
  const [query, setQuery] = useState('');
  const guides = [
    ['开始研究', '在顶部搜索框输入主题、论文、作者或会议名称。系统只在你主动提交后搜索。', Search],
    ['文献图谱', '从种子论文展开引文关系，点击节点可查看摘要、来源、DOI 与引用信息。', FileSearch],
    ['时间线与引文网络', '用时间线观察研究演化；用引文网络识别关键节点与直接关联论文。', Clock3],
    ['阅读清单与每周 TODO', '把论文加入阅读库后，可按周一至周日安排“阅读、笔记、复习、复现”等任务，并独立跟踪完成状态。', BookOpenCheck],
    ['收藏与历史', '收藏重要论文；成功搜索会自动写入历史记录，可随时重新执行。', Bookmark],
    ['数据持久化', '阅读清单、收藏、搜索历史与个人资料都会保存在 SQLite 中，容器重启后仍保留。', CheckCircle2],
  ] as const;
  const filtered = guides.filter(([title, text]) => `${title}${text}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="space-y-4">
    <div className="relative max-w-xl"><Search size={17} className="absolute left-3 top-3 text-gray-400" /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索帮助内容" className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-10 pr-4 text-sm outline-none focus:ring-2 focus:ring-[#6D4AFF]" /></div>
    <div className="grid grid-cols-2 gap-4">
      {filtered.map(([title, text, Icon]) => <div key={title} className="rounded-xl border border-gray-200 bg-white p-5"><div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-[#F2EFFF] text-[#6D4AFF]"><Icon size={18} /></div><h3 className="font-semibold text-gray-900">{title}</h3><p className="mt-2 text-sm leading-6 text-gray-500">{text}</p></div>)}
    </div>
  </div>;
}

function DashboardView({ onRunSearch, onOpenReadingList }: { onRunSearch: (query: string) => void; onOpenReadingList: () => void }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [tasks, setTasks] = useState<ReadingTask[]>([]);
  const [error, setError] = useState('');
  const [weekStart] = useState(() => startOfWeek(new Date()));
  const weekDays = getWeekDays(weekStart);
  const dashboardWeekStart = weekDays[0].iso;
  const dashboardWeekEnd = weekDays[6].iso;
  useEffect(() => {
    let active = true;
    Promise.all([
      researchService.getDashboard(),
      researchService.listReadingTasks(dashboardWeekStart, dashboardWeekEnd),
    ])
      .then(([dashboard, weeklyTasks]) => {
        if (!active) return;
        setData(dashboard);
        setTasks(weeklyTasks);
      })
      .catch((e) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [dashboardWeekEnd, dashboardWeekStart]);
  if (error) return <ErrorBox text={error} />;
  if (!data) return <Loading />;
  const cards = [
    ['搜索次数', data.history_count, History],
    ['阅读清单', data.reading_count, BookOpenCheck],
    ['收藏论文', data.favorite_count, Bookmark],
    ['已读论文', data.reading_statuses.done || 0, CheckCircle2],
    ['Markdown 笔记', data.note_count || 0, PenTool],
  ] as const;

  const toggleTask = async (task: ReadingTask) => {
    try {
      const updated = await researchService.updateReadingTask(task.id, { status: task.status === 'done' ? 'todo' : 'done' });
      setTasks((current) => current.map((item) => item.id === task.id ? updated : item));
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新本周任务失败');
    }
  };

  return <div className="space-y-6">
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">{cards.map(([label, value, Icon]) => <div key={label} className="rounded-xl border border-gray-200 bg-white p-5"><div className="flex items-center justify-between"><div className="text-sm text-gray-500">{label}</div><Icon size={18} className="text-[#6D4AFF]" /></div><div className="mt-3 text-3xl font-bold text-gray-900">{value}</div></div>)}</div>
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 font-semibold text-gray-900"><CalendarDays size={18} className="text-[#6D4AFF]" />本周阅读 TODO</div>
          <div className="mt-1 text-xs text-gray-400">直接从仪表盘确认这一周每天要读什么、做什么。</div>
        </div>
        <button onClick={onOpenReadingList} className="rounded-lg border border-[#D8CEFF] bg-[#F8F6FF] px-3 py-2 text-sm font-medium text-[#6D4AFF] hover:bg-[#F2EFFF]">打开完整计划</button>
      </div>
      {tasks.length ? (
        <div className="overflow-x-auto pb-1">
          <div className="grid min-w-[900px] grid-cols-7 gap-2">
            {weekDays.map((day) => {
              const dayTasks = tasks.filter((task) => task.scheduled_date === day.iso);
              return <div key={day.iso} className={`min-h-36 rounded-lg border p-2.5 ${day.isToday ? 'border-[#9D87FF] bg-[#FAF9FF]' : 'border-gray-100 bg-gray-50/60'}`}>
                <div className="mb-2 flex items-center justify-between"><span className={`text-xs font-semibold ${day.isToday ? 'text-[#6D4AFF]' : 'text-gray-700'}`}>{day.weekday}</span><span className="text-[10px] text-gray-400">{day.shortDate}</span></div>
                <div className="space-y-1.5">
                  {dayTasks.slice(0, 3).map((task) => <button key={task.id} onClick={() => toggleTask(task)} className={`flex w-full items-start gap-1.5 rounded-md border bg-white p-2 text-left ${task.status === 'done' ? 'border-emerald-100 opacity-60' : 'border-gray-100'}`} title={task.status === 'done' ? '点击恢复为待完成' : '点击标记完成'}>
                    {task.status === 'done' ? <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-emerald-500" /> : <Circle size={13} className="mt-0.5 shrink-0 text-gray-300" />}
                    <span className="min-w-0"><span className="block truncate text-[11px] font-medium text-gray-800">{task.task_text}</span><span className="mt-0.5 block truncate text-[10px] text-gray-400">{task.paper.titleEn}</span></span>
                  </button>)}
                  {dayTasks.length > 3 && <div className="text-center text-[10px] text-gray-400">还有 {dayTasks.length - 3} 项</div>}
                  {!dayTasks.length && <div className="pt-6 text-center text-[10px] text-gray-300">空闲</div>}
                </div>
              </div>;
            })}
          </div>
        </div>
      ) : (
        <button onClick={onOpenReadingList} className="flex w-full flex-col items-center justify-center rounded-lg border border-dashed border-gray-200 py-10 text-gray-400 hover:border-[#CFC3FF] hover:bg-[#FCFBFF] hover:text-[#6D4AFF]"><CalendarDays size={28} /><span className="mt-2 text-sm font-medium">本周还没有安排任务</span><span className="mt-1 text-xs">点击进入阅读清单，把论文排到周一至周日。</span></button>
      )}
    </div>
    <div className="grid grid-cols-[1fr_320px] gap-5">
      <div className="rounded-xl border border-gray-200 bg-white p-5"><h3 className="font-semibold text-gray-900">最近搜索</h3><div className="mt-4 divide-y divide-gray-100">{data.recent_searches.length ? data.recent_searches.map(item => <button key={item.id} onClick={() => onRunSearch(item.query)} className="flex w-full items-center justify-between py-3 text-left hover:text-[#6D4AFF]"><div><div className="text-sm font-medium">{item.query}</div><div className="mt-1 text-xs text-gray-400">{item.result_count} 篇论文 · {formatTime(item.created_at)}</div></div><ArrowRight size={16} /></button>) : <Empty text="还没有搜索历史" />}</div></div>
      <div className="rounded-xl border border-gray-200 bg-white p-5"><h3 className="font-semibold text-gray-900">阅读进度</h3><div className="mt-5 space-y-4"><Progress label="待读" value={data.reading_statuses.to_read || 0} total={data.reading_count} /><Progress label="在读" value={data.reading_statuses.reading || 0} total={data.reading_count} /><Progress label="已读" value={data.reading_statuses.done || 0} total={data.reading_count} /></div></div>
    </div>
  </div>;
}

function HistoryView({ onRunSearch }: { onRunSearch: (query: string) => void }) {
  const [items, setItems] = useState<SearchHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    researchService.listHistory()
      .then((data) => { if (active) setItems(data); })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  if (loading) return <Loading />;
  if (error) return <ErrorBox text={error} />;
  return <div className="rounded-xl border border-gray-200 bg-white">
    <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4"><div className="text-sm text-gray-500">共 {items.length} 条搜索记录</div><button disabled={!items.length} onClick={async () => { await researchService.clearHistory(); setItems([]); }} className="flex items-center gap-2 text-sm text-red-500 disabled:opacity-40"><Trash2 size={15} />清空历史</button></div>
    {items.length ? <div className="divide-y divide-gray-100">{items.map(item => <div key={item.id} className="flex items-center gap-4 px-5 py-4"><div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-50 text-gray-400"><History size={18} /></div><div className="min-w-0 flex-1"><div className="font-medium text-gray-900">{item.query}</div><div className="mt-1 truncate text-xs text-gray-400">{item.seed_title || '研究图谱'} · {item.result_count} 篇 · {formatTime(item.created_at)}</div></div><button onClick={() => onRunSearch(item.query)} className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-[#6D4AFF] hover:bg-[#F8F6FF]">重新搜索</button><button onClick={async () => { await researchService.removeHistory(item.id); setItems(current => current.filter(x => x.id !== item.id)); }} className="p-2 text-gray-300 hover:text-red-500"><Trash2 size={16} /></button></div>)}</div> : <Empty text="还没有搜索历史" />}
  </div>;
}

function FavoritesView({ favorites, onSelect, onRemove }: { favorites: FavoriteItem[]; onSelect: (paperId: string) => void; onRemove: (paperId: string) => void }) {
  if (!favorites.length) return <div className="rounded-xl border border-dashed border-gray-300 bg-white py-20"><Empty text="还没有收藏论文，在论文详情中点击书签即可收藏" /></div>;
  return <div className="grid grid-cols-2 gap-4">{favorites.map(({ paper, created_at }) => <div key={paper.id} className="rounded-xl border border-gray-200 bg-white p-5"><div className="flex items-start justify-between gap-4"><div className="min-w-0"><div className="text-xs font-semibold text-[#6D4AFF]">{paper.venue || 'Unknown venue'} · {paper.year || '—'}</div><button onClick={() => onSelect(paper.id)} className="mt-2 text-left font-semibold leading-6 text-gray-900 hover:text-[#6D4AFF]">{paper.titleZh || paper.titleEn}</button><div className="mt-2 line-clamp-1 text-xs text-gray-400">{paper.authors.join(', ')}</div></div><button onClick={() => onRemove(paper.id)} className="rounded-lg p-2 text-[#6D4AFF] hover:bg-[#F2EFFF]" title="取消收藏"><Bookmark size={18} fill="currentColor" /></button></div><div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-xs text-gray-400"><span>被引 {paper.citations}</span><span>收藏于 {formatTime(created_at)}</span></div></div>)}</div>;
}

function NotesView() {
  const [items, setItems] = useState<NoteItem[]>([]);
  const [selected, setSelected] = useState<NoteItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    researchService.listNotes()
      .then((data) => { if (active) { setItems(data); setSelected(data[0] || null); } })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  if (loading) return <Loading />;
  if (error) return <ErrorBox text={error} />;
  if (!items.length) return <div className="rounded-xl border border-dashed border-gray-300 bg-white py-20"><Empty text="还没有 Markdown 笔记。打开任意论文详情，在“阅读笔记”中创建或导入 .md 文件。" /></div>;

  const saveSelected = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await researchService.saveNote(selected.paper, selected.title, selected.content);
      setSelected(updated);
      setItems((current) => [updated, ...current.filter((item) => item.paper.id !== updated.paper.id)]);
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存笔记失败');
    } finally {
      setSaving(false);
    }
  };

  const removeSelected = async () => {
    if (!selected) return;
    await researchService.removeNote(selected.paper.id);
    const remaining = items.filter((item) => item.paper.id !== selected.paper.id);
    setItems(remaining);
    setSelected(remaining[0] || null);
  };

  return <div className="grid min-h-[620px] grid-cols-[300px_minmax(0,1fr)] overflow-hidden rounded-xl border border-gray-200 bg-white">
    <div className="border-r border-gray-200 bg-gray-50/50 p-3">
      <div className="mb-3 px-2 text-xs font-semibold uppercase tracking-wider text-gray-400">{items.length} 篇笔记</div>
      <div className="space-y-2">{items.map((item) => <button key={item.paper.id} onClick={() => setSelected(item)} className={`w-full overflow-hidden rounded-lg border p-3 text-left ${selected?.paper.id === item.paper.id ? 'border-[#B9A8FF] bg-[#F8F6FF]' : 'border-gray-200 bg-white hover:border-gray-300'}`}>
        <div className="truncate text-sm font-semibold text-gray-900">{item.title || item.paper.titleEn}</div>
        <div className="mt-1 truncate text-xs text-gray-500">{item.paper.titleEn}</div>
        <div className="mt-2 text-[11px] text-gray-400">更新于 {formatTime(item.updated_at)}</div>
      </button>)}</div>
    </div>
    {selected && <div className="flex min-w-0 flex-col p-5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="min-w-0"><div className="truncate text-xs text-gray-400">关联论文：{selected.paper.titleEn}</div><input value={selected.title} onChange={(e) => setSelected({ ...selected, title: e.target.value })} className="mt-2 w-full border-0 p-0 text-xl font-bold text-gray-900 outline-none" /></div>
        <div className="flex shrink-0 gap-2">
          <label className="flex cursor-pointer items-center gap-1 rounded-lg border border-gray-200 px-3 py-2 text-xs text-gray-600 hover:bg-gray-50"><Upload size={14} />导入 .md<input type="file" accept=".md,text/markdown,text/plain" className="hidden" onChange={async (e) => { const file = e.target.files?.[0]; if (file) setSelected({ ...selected, title: file.name.replace(/\.md$/i, '') || selected.title, content: await file.text() }); e.currentTarget.value = ''; }} /></label>
          <button onClick={() => downloadMarkdown(selected.title || selected.paper.titleEn, selected.content)} className="flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-2 text-xs text-gray-600 hover:bg-gray-50"><Download size={14} />导出</button>
          <button onClick={removeSelected} className="rounded-lg border border-red-100 p-2 text-red-400 hover:bg-red-50"><Trash2 size={15} /></button>
        </div>
      </div>
      <textarea value={selected.content} onChange={(e) => setSelected({ ...selected, content: e.target.value })} spellCheck={false} className="min-h-[470px] flex-1 resize-none rounded-xl border border-gray-200 bg-[#FCFCFD] p-4 font-mono text-sm leading-7 text-gray-700 outline-none focus:border-[#B9A8FF] focus:ring-2 focus:ring-[#6D4AFF]/10" />
      <div className="mt-4 flex items-center justify-between"><div className="text-xs text-gray-400">Markdown 原文 · {selected.content.length.toLocaleString()} 字符</div><button disabled={saving} onClick={saveSelected} className="flex items-center gap-2 rounded-lg bg-[#6D4AFF] px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"><Save size={15} />{saving ? '保存中...' : '保存笔记'}</button></div>
    </div>}
  </div>;
}

function ProfileView() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { researchService.getProfile().then(setProfile).catch((e) => setError(e.message)); }, []);
  if (error) return <ErrorBox text={error} />;
  if (!profile) return <Loading />;
  const update = (key: keyof UserProfile, value: string) => setProfile(current => current ? { ...current, [key]: value } : current);
  return <div className="max-w-3xl rounded-xl border border-gray-200 bg-white p-6">
    <div className="mb-6 flex items-center gap-4"><div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#F2EFFF] text-[#6D4AFF]"><User size={24} /></div><div><div className="text-lg font-semibold text-gray-900">{profile.display_name || '研究者'}</div><div className="text-sm text-gray-400">本地研究资料 · SQLite 持久化</div></div></div>
    <div className="grid grid-cols-2 gap-5"><Field label="显示名称" value={profile.display_name} onChange={(v) => update('display_name', v)} /><Field label="身份 / 职位" value={profile.role} onChange={(v) => update('role', v)} /><Field label="机构" value={profile.institution} onChange={(v) => update('institution', v)} /><div /><div className="col-span-2"><label className="mb-2 block text-sm font-medium text-gray-700">研究兴趣</label><textarea value={profile.research_interests} onChange={(e) => update('research_interests', e.target.value)} rows={5} placeholder="例如：后量子密码、零知识证明、注册式加密" className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#6D4AFF]" /></div></div>
    <div className="mt-6 flex items-center gap-3"><button disabled={saving} onClick={async () => { setSaving(true); setSaved(false); try { const updated = await researchService.updateProfile(profile); setProfile(updated); setSaved(true); } catch (e) { setError(e instanceof Error ? e.message : '保存失败'); } finally { setSaving(false); } }} className="rounded-lg bg-[#6D4AFF] px-5 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50">{saving ? '保存中...' : '保存资料'}</button>{saved && <span className="flex items-center gap-1 text-sm text-green-600"><CheckCircle2 size={15} />已保存</span>}</div>
  </div>;
}

function AccountView() {
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [currentPassword, setCurrentPassword] = useState('');
  const [username, setUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    authService.account()
      .then((data) => { if (active) { setAccount(data); setUsername(data.username); } })
      .catch((e) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);

  if (!account && !error) return <Loading />;

  const saveCredentials = async () => {
    if (newPassword && newPassword !== confirmPassword) return setError('两次输入的新密码不一致');
    if (newPassword && newPassword.length < 10) return setError('新密码至少 10 位');
    setBusy(true); setError(''); setMessage('');
    try {
      const updated = await authService.updateCredentials({
        current_password: currentPassword,
        username: username.trim() || undefined,
        new_password: newPassword || undefined,
      });
      setAccount(updated);
      setUsername(updated.username);
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('');
      setMessage('账户凭据已更新，会话已安全轮换。');
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败');
    } finally { setBusy(false); }
  };

  const importBackup = async (file: File) => {
    if (!window.confirm('导入会替换当前阅读清单、TODO、收藏、历史、个人资料和笔记。登录账号与密码不会被覆盖。确定继续吗？')) return;
    setBusy(true); setError(''); setMessage('');
    try {
      await authService.importBackup(file);
      setMessage('备份恢复完成，页面即将刷新。');
      window.setTimeout(() => window.location.reload(), 700);
    } catch (e) {
      setError(e instanceof Error ? e.message : '导入失败');
    } finally { setBusy(false); }
  };

  return <div className="space-y-5">
    {error && <ErrorBox text={error} />}
    {message && <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{message}</div>}
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="mb-5 flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#F2EFFF] text-[#6D4AFF]"><KeyRound size={19} /></div><div><h3 className="font-semibold text-gray-900">登录凭据</h3><p className="text-xs text-gray-400">密码使用 scrypt 哈希保存，不存储明文。</p></div></div>
        <div className="space-y-4">
          <Field label="用户名" value={username} onChange={setUsername} />
          <PasswordInput label="当前密码（修改时必填）" value={currentPassword} onChange={setCurrentPassword} />
          <PasswordInput label="新密码（留空则不修改，至少 10 位）" value={newPassword} onChange={setNewPassword} />
          <PasswordInput label="确认新密码" value={confirmPassword} onChange={setConfirmPassword} />
          <button disabled={busy || !currentPassword} onClick={saveCredentials} className="rounded-lg bg-[#6D4AFF] px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-40">保存账户设置</button>
        </div>
        {account && <div className="mt-5 border-t border-gray-100 pt-4 text-xs text-gray-400">当前活跃会话：{account.active_sessions} · 凭据更新于 {formatTime(account.updated_at)}</div>}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="mb-5 flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600"><DatabaseBackup size={19} /></div><div><h3 className="font-semibold text-gray-900">数据备份与恢复</h3><p className="text-xs text-gray-400">备份不包含密码哈希、Cookie 或会话 token。</p></div></div>
        <div className="space-y-3">
          <button disabled={busy} onClick={() => authService.downloadBackup().catch((e) => setError(e.message))} className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"><Download size={16} />导出完整研究备份</button>
          <label className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-[#B9A8FF] bg-[#FAF9FF] px-4 py-3 text-sm font-medium text-[#6D4AFF] hover:bg-[#F4F1FF]"><Upload size={16} />导入备份 JSON<input type="file" accept="application/json,.json" className="hidden" disabled={busy} onChange={(e) => { const file = e.target.files?.[0]; if (file) void importBackup(file); e.currentTarget.value = ''; }} /></label>
        </div>
        <div className="mt-4 rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-700">导入前会严格校验格式、数据行数、论文 JSON 和数据库约束；恢复过程使用 SQLite 事务，失败会整体回滚。</div>
      </div>
    </div>

    <div className="rounded-xl border border-red-100 bg-white p-6">
      <div className="mb-3 flex items-center gap-2 font-semibold text-gray-900"><LogOut size={18} className="text-red-500" />会话</div>
      <p className="mb-4 text-sm text-gray-500">退出会立即删除当前服务器会话 Cookie。</p>
      <button onClick={async () => { await authService.logout(); window.location.reload(); }} className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50">退出登录</button>
    </div>
  </div>;
}

function PasswordInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <div><label className="mb-2 block text-sm font-medium text-gray-700">{label}</label><input type="password" autoComplete="new-password" value={value} onChange={(e) => onChange(e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#6D4AFF]" /></div>; }

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <div><label className="mb-2 block text-sm font-medium text-gray-700">{label}</label><input value={value} onChange={(e) => onChange(e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#6D4AFF]" /></div>; }
function Loading() { return <div className="flex h-64 items-center justify-center text-gray-400"><Loader2 size={24} className="mr-2 animate-spin" />正在加载...</div>; }
function ErrorBox({ text }: { text: string }) { return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">{text}</div>; }
function Empty({ text }: { text: string }) { return <div className="py-10 text-center text-sm text-gray-400">{text}</div>; }
function Progress({ label, value, total }: { label: string; value: number; total: number }) { const pct = total ? Math.round(value / total * 100) : 0; return <div><div className="mb-1.5 flex justify-between text-sm"><span className="text-gray-600">{label}</span><span className="font-medium text-gray-900">{value}</span></div><div className="h-2 overflow-hidden rounded-full bg-gray-100"><div className="h-full rounded-full bg-[#6D4AFF]" style={{ width: `${pct}%` }} /></div></div>; }
function formatTime(value: string) { const normalized = value.includes('T') ? value : `${value.replace(' ', 'T')}Z`; const date = new Date(normalized); return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }); }
function downloadMarkdown(title: string, content: string) { const safe = (title || 'reading-note').replace(/[\\/:*?"<>|]+/g, '-').slice(0, 120); const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${safe}.md`; anchor.click(); URL.revokeObjectURL(url); }
