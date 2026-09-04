'use client';

import React, { useState } from 'react';
import { FileCode, Plus, X, AlertCircle } from 'lucide-react';
import { CodingFile, useCodingStore } from '@/lib/stores/use-coding-store';

interface FileTabsProps {
  isLocked: boolean;
  onAddFile: (path: string, name: string) => Promise<void>;
  onDeleteFile: (fileId: string) => Promise<void>;
}

export const FileTabs: React.FC<FileTabsProps> = ({ isLocked, onAddFile, onDeleteFile }) => {
  const { files, activeFileId, setActiveFileId } = useCodingStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newFilePath, setNewFilePath] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleCreateFile = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const trimmed = newFilePath.trim();
    if (!trimmed) {
      setErrorMsg('File name cannot be empty');
      return;
    }

    if (trimmed.includes('..') || trimmed.startsWith('/') || trimmed.startsWith('\\')) {
      setErrorMsg('Path traversal is forbidden (no .., leading slashes)');
      return;
    }

    try {
      const fileName = trimmed.split('/').pop() || trimmed;
      await onAddFile(trimmed, fileName);
      setNewFilePath('');
      setIsModalOpen(false);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create file');
    }
  };

  return (
    <div className="flex items-center justify-between bg-slate-950/80 border-b border-slate-800/80 px-2 overflow-x-auto scrollbar-none">
      <div className="flex items-center gap-1 py-1">
        {files.map((file) => {
          const isActive = file.id === activeFileId;
          return (
            <div
              key={file.id}
              onClick={() => setActiveFileId(file.id)}
              className={`group flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md cursor-pointer transition-all border ${
                isActive
                  ? 'bg-slate-900 text-indigo-300 border-slate-700/80 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50 border-transparent'
              }`}
            >
              <FileCode className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
              <span className="truncate max-w-[120px]">{file.name}</span>

              {files.length > 1 && !isLocked && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteFile(file.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 hover:text-rose-400 p-0.5 rounded transition-opacity"
                  title="Close file"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}

        {/* Add File Button */}
        {!isLocked && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 rounded-md transition-colors"
            title="New File"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New File</span>
          </button>
        )}
      </div>

      {/* New File Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white">Create New Workspace File</h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateFile} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  File Path / Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. solution.py, utils/helpers.js"
                  value={newFilePath}
                  onChange={(e) => setNewFilePath(e.target.value)}
                  autoFocus
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {errorMsg && (
                <div className="flex items-center gap-2 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors shadow-sm"
                >
                  Create File
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
