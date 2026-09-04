'use client';

import React from 'react';
import { X, LayoutTemplate, ArrowRight } from 'lucide-react';
import { useWhiteboardStore } from '@/lib/stores/use-whiteboard-store';
import { SYSTEM_DESIGN_TEMPLATES, SystemDesignTemplate } from './system-design-templates';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface TemplatesDrawerProps {
  onLoadTemplate: (template: SystemDesignTemplate) => void;
}

export const TemplatesDrawer: React.FC<TemplatesDrawerProps> = ({ onLoadTemplate }) => {
  const { isTemplatesDrawerOpen, setIsTemplatesDrawerOpen } = useWhiteboardStore();

  if (!isTemplatesDrawerOpen) return null;

  return (
    <div className="fixed inset-y-0 left-0 z-50 w-80 lg:w-96 bg-slate-950/95 border-r border-slate-800 shadow-2xl backdrop-blur-md flex flex-col animate-in slide-in-from-left duration-200">
      {/* Header */}
      <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <LayoutTemplate className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-bold text-white">Architecture Templates</h3>
        </div>
        <button
          onClick={() => setIsTemplatesDrawerOpen(false)}
          className="p-1 text-slate-400 hover:text-white rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Templates List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {SYSTEM_DESIGN_TEMPLATES.map((tmpl) => (
          <Card
            key={tmpl.id}
            className="p-3.5 bg-slate-900/80 border-slate-800 hover:border-slate-700 transition-colors space-y-2.5"
          >
            <div>
              <span className="text-[10px] text-indigo-400 font-mono block uppercase tracking-wider">
                {tmpl.category}
              </span>
              <h4 className="text-xs font-bold text-white mt-0.5">{tmpl.name}</h4>
              <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                {tmpl.description}
              </p>
            </div>

            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
              <span className="text-[10px] text-slate-500 font-mono">
                {tmpl.nodes.length} Components
              </span>
              <Button
                size="sm"
                onClick={() => onLoadTemplate(tmpl)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] h-7 px-3 flex items-center gap-1"
              >
                <span>Load Template</span>
                <ArrowRight className="w-3 h-3" />
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
