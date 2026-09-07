'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useWhiteboardStore } from '@/lib/stores/use-whiteboard-store';
import { WhiteboardToolbar } from './whiteboard-toolbar';
import { WhiteboardCanvas } from './whiteboard-canvas';
import { StencilsDrawer } from './stencils-drawer';
import { TemplatesDrawer } from './templates-drawer';
import { WhiteboardSnapshotsDrawer } from './whiteboard-snapshots-drawer';
import { PrivateLayerDrawer } from './private-layer-drawer';
import { SYSTEM_DESIGN_STENCILS, SystemDesignStencil } from './system-design-stencils';
import { SystemDesignTemplate } from './system-design-templates';
import { RealtimeClient } from '@/lib/realtime/realtime-client';
import { apiClient } from '@/lib/api';
import { createShapeId, Editor } from 'tldraw';

interface WhiteboardWorkspaceProps {
  sessionId: string;
  interviewId: string;
  isInterviewer: boolean;
  token?: string;
  realtimeClient: RealtimeClient | null;
}

export const WhiteboardWorkspace: React.FC<WhiteboardWorkspaceProps> = ({
  sessionId,
  interviewId,
  isInterviewer,
  token,
  realtimeClient,
}) => {
  const {
    whiteboard,
    isLocked,
    setWhiteboard,
    setIsLocked,
    setIsTemplatesDrawerOpen,
    setIsStencilsDrawerOpen,
  } = useWhiteboardStore();

  const [isLoading, setIsLoading] = useState(true);
  const [activeTool, setActiveTool] = useState('select');
  const editorRef = useRef<Editor | null>(null);

  // 1. Fetch or initialize whiteboard session
  const fetchWhiteboard = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await apiClient<any>(`/sessions/${sessionId}/whiteboard`);
      setWhiteboard(data);
    } catch (err) {
      console.error('Failed to fetch whiteboard session:', err);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, setWhiteboard]);

  useEffect(() => {
    fetchWhiteboard();
  }, [fetchWhiteboard]);

  // 2. Handle Editor Ready callback
  const handleEditorReady = useCallback((editor: Editor) => {
    editorRef.current = editor;
  }, []);

  // 3. Tool Selection Handler
  const handleSelectTool = (tool: string) => {
    setActiveTool(tool);
    if (!editorRef.current) return;

    if (tool === 'select') {
      editorRef.current.setCurrentTool('select');
    } else if (tool === 'draw') {
      editorRef.current.setCurrentTool('draw');
    } else if (tool === 'text') {
      editorRef.current.setCurrentTool('text');
    } else if (tool === 'geo_rectangle') {
      editorRef.current.setCurrentTool('geo');
    } else if (tool === 'geo_ellipse') {
      editorRef.current.setCurrentTool('geo');
    } else if (tool === 'arrow') {
      editorRef.current.setCurrentTool('arrow');
    } else if (tool === 'note') {
      editorRef.current.setCurrentTool('note');
    } else if (tool === 'eraser') {
      editorRef.current.setCurrentTool('eraser');
    }
  };

  // 4. Undo / Redo
  const handleUndo = () => {
    if (editorRef.current) {
      editorRef.current.undo();
    }
  };

  const handleRedo = () => {
    if (editorRef.current) {
      editorRef.current.redo();
    }
  };

  // 5. Lock / Unlock Toggle
  const handleToggleLock = async () => {
    if (!whiteboard || !isInterviewer) return;
    try {
      const newLocked = !isLocked;
      await apiClient(`/whiteboards/${whiteboard.id}/lock`, {
        method: 'POST',
        body: JSON.stringify({ is_locked: newLocked }),
      });
      setIsLocked(newLocked);

      realtimeClient?.emit('whiteboard_lock_state', {
        is_locked: newLocked,
      });
    } catch (err) {
      console.error('Failed to toggle lock:', err);
    }
  };

  // 6. Clear Board
  const handleClear = async () => {
    if (!whiteboard || !isInterviewer) return;
    if (!confirm('Are you sure you want to clear the entire whiteboard?')) return;

    try {
      await apiClient(`/whiteboards/${whiteboard.id}/clear`, {
        method: 'POST',
      });

      if (editorRef.current) {
        const allShapeIds = Array.from(editorRef.current.getCurrentPageShapeIds());
        if (allShapeIds.length > 0) {
          editorRef.current.deleteShapes(allShapeIds);
        }
      }

      realtimeClient?.emit('whiteboard_clear');
    } catch (err) {
      console.error('Failed to clear whiteboard:', err);
    }
  };

  // 7. Insert Stencil Component
  const handleInsertStencil = (stencil: SystemDesignStencil) => {
    if (!editorRef.current) return;

    const viewportCenter = editorRef.current.getViewportPageBounds().center;
    const shapeId = createShapeId();

    editorRef.current.createShapes([
      {
        id: shapeId,
        type: 'geo',
        x: viewportCenter.x - stencil.defaultWidth / 2,
        y: viewportCenter.y - stencil.defaultHeight / 2,
        props: {
          geo: 'rectangle',
          w: stencil.defaultWidth,
          h: stencil.defaultHeight,
          text: stencil.label,
          color: 'violet',
          fill: 'semi',
        },
      },
    ]);

    editorRef.current.select(shapeId);
    setIsStencilsDrawerOpen(false);
  };

  // 8. Load Template
  const handleLoadTemplate = (template: SystemDesignTemplate) => {
    if (!editorRef.current) return;

    // Clear existing shapes
    const allShapeIds = Array.from(editorRef.current.getCurrentPageShapeIds());
    if (allShapeIds.length > 0) {
      editorRef.current.deleteShapes(allShapeIds);
    }

    // Insert nodes
    const nodeMap: Record<string, string> = {};
    const shapesToCreate: any[] = [];

    template.nodes.forEach((node) => {
      const shapeId = createShapeId();
      nodeMap[node.id] = shapeId;

      shapesToCreate.push({
        id: shapeId,
        type: 'geo',
        x: node.x,
        y: node.y,
        props: {
          geo: 'rectangle',
          w: node.w,
          h: node.h,
          text: node.label,
          color: 'blue',
          fill: 'semi',
        },
      });
    });

    // Insert arrows
    template.arrows.forEach((arrow) => {
      const fromId = nodeMap[arrow.from];
      const toId = nodeMap[arrow.to];

      if (fromId && toId) {
        const arrowId = createShapeId();
        shapesToCreate.push({
          id: arrowId,
          type: 'arrow',
          x: 0,
          y: 0,
          props: {
            text: arrow.label || '',
            start: { type: 'binding', boundShapeId: fromId, normalizedAnchor: { x: 0.5, y: 0.5 }, isExact: false, isPrecise: false },
            end: { type: 'binding', boundShapeId: toId, normalizedAnchor: { x: 0.5, y: 0.5 }, isExact: false, isPrecise: false },
          },
        });
      }
    });

    editorRef.current.createShapes(shapesToCreate);
    setIsTemplatesDrawerOpen(false);
  };

  // 9. Export
  const handleExport = async (format: 'png' | 'svg' | 'json') => {
    if (!editorRef.current) return;

    if (format === 'json') {
      const snap = editorRef.current.store.getSnapshot();
      const blob = new Blob([JSON.stringify(snap, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `whiteboard-${sessionId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      // Direct snapshot JSON fallback or download
      alert(`Exporting ${format.toUpperCase()} image of your system design diagram.`);
    }
  };

  if (isLoading || !whiteboard) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-950 text-slate-400 text-xs">
        Loading Collaborative Whiteboard & System Design Canvas...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-950 overflow-hidden relative">
      {/* Top Whiteboard Toolbar */}
      <WhiteboardToolbar
        isInterviewer={isInterviewer}
        activeTool={activeTool}
        onSelectTool={handleSelectTool}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onToggleLock={handleToggleLock}
        onClear={handleClear}
        onExport={handleExport}
        onInsertStencil={(id) => {
          const st = SYSTEM_DESIGN_STENCILS.find((s) => s.id === id);
          if (st) handleInsertStencil(st);
        }}
      />

      {/* Main Canvas Area */}
      <div className="flex-1 relative overflow-hidden">
        <WhiteboardCanvas
          whiteboardId={whiteboard.id}
          isInterviewer={isInterviewer}
          realtimeClient={realtimeClient}
          onEditorReady={handleEditorReady}
        />
      </div>

      {/* Slide-over Drawers */}
      <StencilsDrawer onInsertStencil={handleInsertStencil} />
      <TemplatesDrawer onLoadTemplate={handleLoadTemplate} />
      <WhiteboardSnapshotsDrawer
        whiteboardId={whiteboard.id}
        isInterviewer={isInterviewer}
        realtimeClient={realtimeClient}
        onSnapshotRestored={(doc) => {
          if (editorRef.current && doc) {
            editorRef.current.loadSnapshot(doc);
          }
        }}
      />
      <PrivateLayerDrawer
        whiteboardId={whiteboard.id}
        realtimeClient={realtimeClient}
      />
    </div>
  );
};
