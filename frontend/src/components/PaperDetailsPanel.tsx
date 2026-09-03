'use client';

import React, { useEffect, useState } from 'react';
import { Bookmark, FileText, ExternalLink, CheckCircle2, BookOpenCheck, Download, Save, Upload } from 'lucide-react';
import { Paper } from '../types/paper';
import { categoryColors } from '../constants/categories';
import { researchService } from '../services/researchService';

const getCategoryZh = (cat: string) => {
  const map: Record<string, string> = {
    'foundation': '基础理论论文',
    'security': '安全性论文',
    'efficiency': '效率优化论文',
    'scalability': '大规模与扩展性论文',
    'variant': '变体与扩展论文',
    'application': '应用与实践论文'
  };
  return map[cat] || '其他论文';
};

export default function PaperDetailsPanel({
  paper,
  inReadingList = false,
  isFavorite = false,
  onAddReading,
  onToggleFavorite,
}: {
  paper: Paper | null;
  inReadingList?: boolean;
  isFavorite?: boolean;
  onAddReading?: (paper: Paper) => void;
  onToggleFavorite?: (paper: Paper) => void;
}) {
  const [showFullAbstract, setShowFullAbstract] = useState(false);
  const [noteTitle, setNoteTitle] = useState('');
  const [noteContent, setNoteContent] = useState('');
  const [noteLoading, setNoteLoading] = useState(true);
  const [noteSaving, setNoteSaving] = useState(false);
  const [noteSaved, setNoteSaved] = useState(false);
  const [noteError, setNoteError] = useState('');

  useEffect(() => {
    if (!paper) return;
    let active = true;
    researchService.getNote(paper.id)
      .then((note) => {
        if (!active) return;
        if (note) {
          setNoteTitle(note.title || `${paper.titleEn} 阅读笔记`);
          setNoteContent(note.content);
        } else {
          setNoteTitle(`${paper.titleEn} 阅读笔记`);
          setNoteContent(`# ${paper.titleEn}\n\n## 核心问题\n\n## 关键方法\n\n## 主要结论\n\n## 我的理解\n\n## 疑问 / 待验证\n\n## 与其他论文的关系\n\n`);
        }
      })
      .catch((e) => { if (active) setNoteError(e instanceof Error ? e.message : '笔记加载失败'); })
      .finally(() => { if (active) setNoteLoading(false); });
    return () => { active = false; };
  }, [paper]);

  if (!paper) {
    return (
      <aside className="w-[350px] bg-white border-l border-gray-200 h-full p-6 flex flex-col items-center justify-center text-center shrink-0">
        <FileText size={48} className="text-gray-200 mb-4" />
        <h3 className="text-gray-500 font-medium">未选择论文</h3>
        <p className="text-sm text-gray-400 mt-2">请在研究图谱中点击节点以查看详细信息。</p>
      </aside>
    );
  }

  const categoryColor = categoryColors[paper.category] || categoryColors.foundation;
  const eprintUrl = paper.eprint ? `https://eprint.iacr.org/${paper.eprint}` : undefined;
  const pdfUrl = paper.pdfUrl || (paper.eprint ? `https://eprint.iacr.org/${paper.eprint}.pdf` : undefined);
  const primaryUrl = pdfUrl || paper.semanticScholarUrl;

  return (
    <aside className="w-[350px] bg-white border-l border-gray-200 h-full flex flex-col shrink-0 overflow-y-auto">
      <div className="p-6 border-b border-gray-100">
        <div className="text-xs font-bold mb-2" style={{ color: categoryColor }}>
          {paper.venue}
        </div>
        <h2 className="text-xl font-bold text-gray-900 leading-snug mb-1">
          {paper.titleZh}
        </h2>
        <div className="text-sm text-gray-500 mb-3 italic">
          {paper.titleEn}
        </div>
        <div className="text-sm text-gray-600 mb-6">
          {paper.authors.join(', ')}
        </div>
        
        <div className="flex items-center gap-2">
          <a
            href={primaryUrl}
            target="_blank"
            rel="noreferrer"
            className={`flex-1 font-medium py-2 rounded-lg flex justify-center items-center gap-2 transition-colors text-sm ${primaryUrl ? 'bg-[#6D4AFF] hover:bg-purple-700 text-white' : 'bg-gray-100 text-gray-400 pointer-events-none'}`}
          >
            <FileText size={16} />
            {pdfUrl ? '查看 PDF' : '查看论文'}
          </a>
          {paper.semanticScholarUrl && (
            <a href={paper.semanticScholarUrl} target="_blank" rel="noreferrer" className="px-4 py-2 bg-gray-50 border border-gray-200 hover:bg-gray-100 text-gray-700 font-medium rounded-lg flex items-center gap-2 transition-colors text-sm" title="Semantic Scholar">
              <ExternalLink size={16} />
              来源
            </a>
          )}
          <button 
            onClick={() => onToggleFavorite?.(paper)}
            disabled={!onToggleFavorite}
            className={`w-10 h-10 flex items-center justify-center border rounded-lg transition-colors ${
              isFavorite 
                ? 'bg-[#F2EFFF] border-[#6D4AFF] text-[#6D4AFF]' 
                : 'bg-gray-50 border-gray-200 text-gray-400 hover:bg-gray-100 hover:text-[#6D4AFF]'
            } disabled:cursor-not-allowed`} 
            title={isFavorite ? "取消收藏" : "收藏"}
          >
            <Bookmark size={18} fill={isFavorite ? 'currentColor' : 'none'} />
          </button>
        </div>
        <button
          type="button"
          disabled={inReadingList || !onAddReading}
          onClick={() => onAddReading?.(paper)}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-[#D8CEFF] bg-[#F8F6FF] py-2 text-sm font-medium text-[#6D4AFF] transition hover:bg-[#F2EFFF] disabled:cursor-default disabled:border-gray-200 disabled:bg-gray-50 disabled:text-gray-400"
        >
          <BookOpenCheck size={16} />
          {inReadingList ? '已加入阅读清单' : '加入阅读清单'}
        </button>
      </div>

      <div className="p-6 space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3 border-l-4 border-[#6D4AFF] pl-2">论文信息</h3>
          <div className="space-y-3 text-sm">
            <div className="flex">
              <span className="w-24 text-gray-500">会议/期刊：</span>
              <span className="flex-1 font-medium text-gray-900">{paper.venueFull || paper.venue}</span>
            </div>
            <div className="flex">
              <span className="w-24 text-gray-500">论文类别：</span>
              <span className="flex-1 text-gray-900">{getCategoryZh(paper.category)}</span>
            </div>
            <div className="flex">
              <span className="w-24 text-gray-500">被引次数：</span>
              <span className="flex-1 text-gray-900">{paper.citations}（来自 Semantic Scholar）</span>
            </div>
            <div className="flex">
              <span className="w-24 text-gray-500">参考文献：</span>
              <span className="flex-1 text-gray-900">{paper.references} 篇</span>
            </div>
            <div className="flex">
              <span className="w-24 text-gray-500">ePrint：</span>
              {eprintUrl ? (
                <a href={eprintUrl} target="_blank" rel="noreferrer" className="flex-1 text-[#6D4AFF] hover:underline">{paper.eprint}</a>
              ) : (
                <span className="flex-1 text-gray-400">未匹配</span>
              )}
            </div>
            <div className="flex">
              <span className="w-24 text-gray-500">来源：</span>
              {paper.semanticScholarUrl ? (
                <a href={paper.semanticScholarUrl} target="_blank" rel="noreferrer" className="flex-1 text-[#6D4AFF] hover:underline break-all">Semantic Scholar</a>
              ) : (
                <span className="flex-1 text-gray-400">暂无</span>
              )}
            </div>
            <div className="flex">
              <span className="w-24 text-gray-500">DOI：</span>
              {paper.doi ? (
                <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer" className="flex-1 break-all text-[#6D4AFF] hover:underline">{paper.doi}</a>
              ) : (
                <span className="flex-1 text-gray-400">暂无</span>
              )}
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-2 border-l-4 border-[#6D4AFF] pl-2">摘要</h3>
          <p className={`text-sm text-gray-600 leading-relaxed ${showFullAbstract ? '' : 'line-clamp-4'}`}>
            {paper.abstractZh}
          </p>
          <button 
            onClick={() => setShowFullAbstract(!showFullAbstract)}
            className="text-[#6D4AFF] text-sm font-medium mt-1 hover:underline"
          >
            {showFullAbstract ? '收起全文' : '展开全文'}
          </button>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="border-l-4 border-[#6D4AFF] pl-2 text-sm font-semibold text-gray-900">阅读笔记（Markdown）</h3>
            {noteSaved && <span className="text-[11px] text-emerald-600">已保存</span>}
          </div>
          <p className="mb-3 text-xs leading-5 text-gray-400">支持直接编辑，也可以导入你本地的 .md 文件；保存后会与当前论文关联并写入 SQLite。</p>
          {noteError && <div className="mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{noteError}</div>}
          {noteLoading ? (
            <div className="rounded-lg border border-gray-200 bg-gray-50 py-8 text-center text-xs text-gray-400">正在加载笔记...</div>
          ) : (
            <>
              <input value={noteTitle} onChange={(e) => { setNoteTitle(e.target.value); setNoteSaved(false); }} className="mb-2 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium outline-none focus:border-[#B9A8FF]" placeholder="笔记标题" />
              <textarea value={noteContent} onChange={(e) => { setNoteContent(e.target.value); setNoteSaved(false); }} spellCheck={false} rows={12} className="w-full resize-y rounded-lg border border-gray-200 bg-[#FCFCFD] p-3 font-mono text-xs leading-6 text-gray-700 outline-none focus:border-[#B9A8FF]" />
              <div className="mt-2 grid grid-cols-3 gap-2">
                <label className="flex cursor-pointer items-center justify-center gap-1 rounded-lg border border-gray-200 py-2 text-xs text-gray-600 hover:bg-gray-50">
                  <Upload size={13} /> 导入 .md
                  <input type="file" accept=".md,text/markdown,text/plain" className="hidden" onChange={async (e) => { const file = e.target.files?.[0]; if (file) { setNoteTitle(file.name.replace(/\.md$/i, '') || noteTitle); setNoteContent(await file.text()); setNoteSaved(false); } e.currentTarget.value = ''; }} />
                </label>
                <button type="button" onClick={() => downloadMarkdown(noteTitle || paper.titleEn, noteContent)} className="flex items-center justify-center gap-1 rounded-lg border border-gray-200 py-2 text-xs text-gray-600 hover:bg-gray-50"><Download size={13} /> 导出 .md</button>
                <button type="button" disabled={noteSaving} onClick={async () => { setNoteSaving(true); setNoteError(''); try { const saved = await researchService.saveNote(paper, noteTitle, noteContent); setNoteTitle(saved.title); setNoteContent(saved.content); setNoteSaved(true); } catch (e) { setNoteError(e instanceof Error ? e.message : '保存失败'); } finally { setNoteSaving(false); } }} className="flex items-center justify-center gap-1 rounded-lg bg-[#6D4AFF] py-2 text-xs font-medium text-white hover:bg-purple-700 disabled:opacity-50"><Save size={13} />{noteSaving ? '保存中' : '保存'}</button>
              </div>
            </>
          )}
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3 border-l-4 border-[#6D4AFF] pl-2">主要贡献</h3>
          <ul className="space-y-2">
            {paper.contributionsZh?.map((contribution, idx) => (
              <li key={idx} className="flex gap-2 text-sm text-gray-600">
                <CheckCircle2 size={16} className="text-[#39B96E] shrink-0 mt-0.5" />
                <span>{contribution}</span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3 border-l-4 border-[#6D4AFF] pl-2">相关主题</h3>
          <div className="flex flex-wrap gap-2">
            {paper.topicsZh?.map((topic, idx) => (
              <span key={idx} className="px-2.5 py-1 bg-[#F2EFFF] text-[#6D4AFF] text-xs font-medium rounded-md">
                {topic}
              </span>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}

function downloadMarkdown(title: string, content: string) {
  const safe = (title || 'reading-note').replace(/[\\/:*?"<>|]+/g, '-').slice(0, 120);
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${safe}.md`;
  anchor.click();
  URL.revokeObjectURL(url);
}
