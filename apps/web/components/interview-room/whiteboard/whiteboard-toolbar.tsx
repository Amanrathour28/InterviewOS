'use client';

import React, { useState } from 'react';
import {
  MousePointer,
  Pencil,
  Type,
  Square,
  Circle,
  ArrowRight,
  StickyNote,
  Eraser,
  Undo2,
  Redo2,
  Lock,
  Unlock,
  Camera,
  Layers,
  Download,
  Trash2,
  Eye,
  EyeOff,
  LayoutTemplate,
  Boxes,
} from 'lucide-react';
import { useWhiteboardStore } from '@/lib/stores/use-whiteboard-store';
import { Button } from '@/components/ui/button';

interface WhiteboardToolbarProps {
  isInterviewer: boolean;
  activeTool: string;
  onSelectTool: (tool: string) => void;
  onUndo: () => void;
  onRedo: () => void;
  onToggleLock: () => void;
  onClear: () => void;
  onExport: (format: 'png' | 'svg' | 'json') => void;
  onInsertStencil: (stencilId: string) => void;
}

export const WhiteboardToolbar: React.FC<WhiteboardToolbarProps> = ({
  isInterviewer,
  activeTool,
  onSelectTool,
  onUndo,
  onRedo,
  onToggleLock,
  onClear,
  onExport,
  onInsertStencil,
}) => {
  const {
    isLocked,
    isPrivateLayerOpen,
    setIsPrivateLayerOpen,
    setIsSnapshotsDrawerOpen,
    setIsTemplatesDrawerOpen,
    setIsStencilsDrawerOpen,
    isStencilsDrawerOpen,
  } = useWhiteboardStore();

  const [isExportOpen, setIsExportOpen] = useState(false);

  const tools = [
    { id: 'select', label: 'Select', icon: MousePointer },
    { id: 'draw', label: 'Draw', icon: Pencil },
    { id: 'text', label: 'Text', icon: Type },
    { id: 'geo_rectangle', label: 'Rectangle', icon: Square },
    { id: 'geo_ellipse', label: 'Ellipse', icon: Circle },
    { id: 'arrow', label: 'Connector Arrow', icon: ArrowRight },
    { id: 'note', label: 'Sticky Note', icon: StickyNote },
    { id: 'eraser', label: 'Eraser', icon: Eraser },
  ];

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 bg-slate-900 border-b border-slate-800 select-none">
      {/* Left: Drawing Tools */}
      <div className="flex items-center gap-1">
        {tools.map((t) => {
          const Icon = t.icon;
          const isSelected = activeTool === t.id;
          const isDisabled = isLocked && !isInterviewer && t.id !== 'select';

          return (
            <button
              key={t.id}
              onClick={() => onSelectTool(t.id)}
              disabled={isDisabled}
              title={t.label}
              className={`p-1.5 rounded-lg text-xs font-medium transition-colors ${
                isSelected
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              } disabled:opacity-40 disabled:hover:bg-transparent`}
            >
              <Icon className="w-4 h-4" />
            </button>
          );
        })}

        <div className="h-4 w-px bg-slate-800 mx-1" />

        {/* Undo / Redo */}
        <button
          onClick={onUndo}
          disabled={isLocked && !isInterviewer}
          title="Undo"
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-40"
        >
          <Undo2 className="w-4 h-4" />
        </button>
        <button
          onClick={onRedo}
          disabled={isLocked && !isInterviewer}
          title="Redo"
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-40"
        >
          <Redo2 className="w-4 h-4" />
        </button>

        <div className="h-4 w-px bg-slate-800 mx-1" />

        {/* System Architecture Stencils Drawer Toggle */}
        <button
          onClick={() => setIsStencilsDrawerOpen(!isStencilsDrawerOpen)}
          disabled={isLocked && !isInterviewer}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
            isStencilsDrawerOpen
              ? 'bg-indigo-950/80 border-indigo-500/50 text-indigo-300'
              : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800'
          } disabled:opacity-40`}
        >
          <Boxes className="w-3.5 h-3.5 text-indigo-400" />
          <span>System Stencils</span>
        </button>
      </div>

      {/* Right: Interviewer Controls, Snapshots, Export */}
      <div className="flex items-center gap-1.5">
        {/* Lock status banner for candidates */}
        {isLocked && (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/30">
            <Lock className="w-3.5 h-3.5 text-amber-400" />
            Locked by Interviewer
          </span>
        )}

        {/* Templates Picker (Interviewer only) */}
        {isInterviewer && (
          <button
            onClick={() => setIsTemplatesDrawerOpen(true)}
            title="Load Architecture Template"
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
          >
            <LayoutTemplate className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">Templates</span>
          </button>
        )}

        {/* Snapshots Checkpoint Drawer */}
        <button
          onClick={() => setIsSnapshotsDrawerOpen(true)}
          title="Whiteboard Milestones"
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
        >
          <Camera className="w-3.5 h-3.5 text-slate-400" />
          <span className="hidden sm:inline">Snapshots</span>
        </button>

        {/* Private Interviewer Layer Toggle */}
        {isInterviewer && (
          <button
            onClick={() => setIsPrivateLayerOpen(!isPrivateLayerOpen)}
            title="Toggle Private Interviewer Layer"
            className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-all ${
              isPrivateLayerOpen
                ? 'bg-purple-950/80 text-purple-300 border-purple-500/50'
                : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
            }`}
          >
            {isPrivateLayerOpen ? (
              <>
                <Eye className="w-3.5 h-3.5 text-purple-400" />
                <span className="hidden sm:inline">Private Layer</span>
              </>
            ) : (
              <>
                <EyeOff className="w-3.5 h-3.5 text-slate-400" />
                <span className="hidden sm:inline">Private Layer</span>
              </>
            )}
          </button>
        )}

        {/* Interviewer Lock Toggle */}
        {isInterviewer && (
          <button
            onClick={onToggleLock}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-all ${
              isLocked
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
                : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
            }`}
          >
            {isLocked ? (
              <>
                <Unlock className="w-3.5 h-3.5 text-amber-400" />
                <span className="hidden md:inline">Unlock</span>
              </>
            ) : (
              <>
                <Lock className="w-3.5 h-3.5 text-slate-400" />
                <span className="hidden md:inline">Lock</span>
              </>
            )}
          </button>
        )}

        {/* Clear Board (Interviewer only) */}
        {isInterviewer && (
          <button
            onClick={onClear}
            title="Clear Shared Canvas"
            className="p-1.5 text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 rounded-lg border border-transparent hover:border-rose-800/50 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}

        {/* Export Menu */}
        <div className="relative">
          <button
            onClick={() => setIsExportOpen(!isExportOpen)}
            title="Export Diagram"
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Export</span>
          </button>

          {isExportOpen && (
            <div className="absolute right-0 mt-1 w-36 bg-slate-900 border border-slate-800 rounded-lg shadow-xl z-50 py-1 text-xs">
              <button
                onClick={() => {
                  onExport('png');
                  setIsExportOpen(false);
                }}
                className="w-full text-left px-3 py-1.5 text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                Export as PNG
              </button>
              <button
                onClick={() => {
                  onExport('svg');
                  setIsExportOpen(false);
                }}
                className="w-full text-left px-3 py-1.5 text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                Export as SVG
              </button>
              <button
                onClick={() => {
                  onExport('json');
                  setIsExportOpen(false);
                }}
                className="w-full text-left px-3 py-1.5 text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                Export JSON State
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
