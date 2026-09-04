'use client';

import React from 'react';
import { X, Boxes, Plus } from 'lucide-react';
import { useWhiteboardStore } from '@/lib/stores/use-whiteboard-store';
import { SYSTEM_DESIGN_STENCILS, SystemDesignStencil } from './system-design-stencils';
import { Card } from '@/components/ui/card';

interface StencilsDrawerProps {
  onInsertStencil: (stencil: SystemDesignStencil) => void;
}

export const StencilsDrawer: React.FC<StencilsDrawerProps> = ({ onInsertStencil }) => {
  const { isStencilsDrawerOpen, setIsStencilsDrawerOpen } = useWhiteboardStore();

  if (!isStencilsDrawerOpen) return null;

  const categories = ['compute', 'storage', 'infrastructure', 'clients'] as const;

  return (
    <div className="fixed inset-y-0 left-0 z-50 w-72 lg:w-80 bg-slate-950/95 border-r border-slate-800 shadow-2xl backdrop-blur-md flex flex-col animate-in slide-in-from-left duration-200">
      {/* Header */}
      <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Boxes className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-bold text-white">System Design Components</h3>
        </div>
        <button
          onClick={() => setIsStencilsDrawerOpen(false)}
          className="p-1 text-slate-400 hover:text-white rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Stencils Body */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {categories.map((cat) => {
          const items = SYSTEM_DESIGN_STENCILS.filter((s) => s.category === cat);
          if (items.length === 0) return null;

          return (
            <div key={cat} className="space-y-1.5">
              <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 pl-1">
                {cat}
              </h4>
              <div className="grid grid-cols-1 gap-1.5">
                {items.map((stencil) => (
                  <button
                    key={stencil.id}
                    onClick={() => onInsertStencil(stencil)}
                    className="p-2.5 bg-slate-900/80 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-800/80 rounded-lg text-left transition-all flex items-center justify-between group"
                  >
                    <div className="flex items-center gap-2.5">
                      <div
                        className="w-3 h-3 rounded-full shrink-0"
                        style={{ backgroundColor: stencil.color }}
                      />
                      <div>
                        <div className="text-xs font-semibold text-slate-200 group-hover:text-white">
                          {stencil.label}
                        </div>
                        <div className="text-[10px] text-slate-500 line-clamp-1">
                          {stencil.description}
                        </div>
                      </div>
                    </div>
                    <Plus className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
