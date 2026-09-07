'use client';

import React, { useEffect, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';
import 'tldraw/tldraw.css';
import { useWhiteboardStore } from '@/lib/stores/use-whiteboard-store';
import { RealtimeClient } from '@/lib/realtime/realtime-client';
import { apiClient } from '@/lib/api';
import { SYSTEM_DESIGN_STENCILS } from './system-design-stencils';
import { SYSTEM_DESIGN_TEMPLATES } from './system-design-templates';
import type { Editor, TLShapeId, createShapeId } from 'tldraw';

// Dynamic import for Tldraw to avoid Next.js SSR issues
const Tldraw = dynamic(() => import('tldraw').then((mod) => mod.Tldraw), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-slate-950 text-slate-400 text-xs">
      Initializing Canvas Engine...
    </div>
  ),
});

interface WhiteboardCanvasProps {
  whiteboardId: string;
  isInterviewer: boolean;
  realtimeClient: RealtimeClient | null;
  onEditorReady?: (editor: Editor) => void;
}

export const WhiteboardCanvas: React.FC<WhiteboardCanvasProps> = ({
  whiteboardId,
  isInterviewer,
  realtimeClient,
  onEditorReady,
}) => {
  const { isLocked, whiteboard, setWhiteboard, setIsLocked, updateCursor } = useWhiteboardStore();
  const editorRef = useRef<Editor | null>(null);
  const isApplyingRemoteUpdate = useRef(false);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 1. Debounced save to PostgreSQL
  const debouncedSaveDocument = useCallback(
    (documentSnapshot: any) => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      saveTimeoutRef.current = setTimeout(async () => {
        try {
          await apiClient(`/whiteboards/${whiteboardId}`, {
            method: 'PATCH',
            body: JSON.stringify({ document: documentSnapshot }),
          });
        } catch (err) {
          console.error('Failed to save whiteboard document:', err);
        }
      }, 1500);
    },
    [whiteboardId]
  );

  // 2. Handle Editor Mount
  const handleMount = useCallback(
    (editor: Editor) => {
      editorRef.current = editor;
      onEditorReady?.(editor);

      // Hydrate authoritative document from store if present
      if (whiteboard?.document && Object.keys(whiteboard.document).length > 0) {
        try {
          isApplyingRemoteUpdate.current = true;
          editor.loadSnapshot(whiteboard.document as any);
        } catch (err) {
          console.error('Failed to load initial whiteboard snapshot:', err);
        } finally {
          isApplyingRemoteUpdate.current = false;
        }
      }

      // Listen for local changes to broadcast and persist
      const cleanupListener = editor.store.listen(
        (change) => {
          if (isApplyingRemoteUpdate.current) return;

          // If locked and candidate, don't propagate
          if (isLocked && !isInterviewer) return;

          // Broadcast pure RecordsDiff { added, updated, removed } rather than HistoryEntry wrapper
          const diff = (change as any)?.changes || change;

          if (realtimeClient) {
            const socket = realtimeClient.getSocket();
            if (socket) {
              socket.emit('whiteboard_patch', {
                changes: diff,
                isLocked,
              });
            }
          }

          // Debounce durable save
          const snap = editor.store.getSnapshot();
          debouncedSaveDocument(snap);
        },
        { scope: 'document', source: 'user' }
      );

      return () => {
        cleanupListener();
      };
    },
    [whiteboard, isLocked, isInterviewer, realtimeClient, debouncedSaveDocument, onEditorReady]
  );

  // 3. Setup Real-time WebSocket Listeners
  useEffect(() => {
    if (!realtimeClient) return;

    const socket = realtimeClient.getSocket();
    if (!socket) return;

    const handleWhiteboardPatch = (data: { changes: any; senderUserId: string }) => {
      if (!editorRef.current || !data.changes) return;

      try {
        let diff = data.changes;
        // Normalize payload if wrapped inside HistoryEntry
        if (diff && typeof diff === 'object' && 'changes' in diff) {
          diff = diff.changes;
        }
        if (!diff || typeof diff !== 'object') return;

        const normalizedDiff = {
          added: diff.added || {},
          updated: diff.updated || {},
          removed: diff.removed || {},
        };

        isApplyingRemoteUpdate.current = true;
        editorRef.current.store.applyDiff(normalizedDiff);
      } catch (err) {
        console.error('Failed to apply remote whiteboard patch:', err);
      } finally {
        isApplyingRemoteUpdate.current = false;
      }
    };

    const handleLockState = (data: { is_locked: boolean }) => {
      setIsLocked(data.is_locked);
      if (editorRef.current && !isInterviewer) {
        editorRef.current.updateInstanceState({ isReadonly: data.is_locked });
      }
    };

    const handleClear = () => {
      if (!editorRef.current) return;
      try {
        isApplyingRemoteUpdate.current = true;
        const allShapeIds = Array.from(editorRef.current.getCurrentPageShapeIds());
        if (allShapeIds.length > 0) {
          editorRef.current.deleteShapes(allShapeIds);
        }
      } finally {
        isApplyingRemoteUpdate.current = false;
      }
    };

    const handleRestore = (data: { document: any }) => {
      if (!editorRef.current || !data.document) return;
      try {
        isApplyingRemoteUpdate.current = true;
        editorRef.current.loadSnapshot(data.document);
      } catch (err) {
        console.error('Failed to load restored snapshot in editor:', err);
      } finally {
        isApplyingRemoteUpdate.current = false;
      }
    };

    const handleCursor = (data: any) => {
      if (data.userId) {
        updateCursor(data);
      }
    };

    socket.on('whiteboard_patch', handleWhiteboardPatch);
    socket.on('whiteboard_lock_state', handleLockState);
    socket.on('whiteboard_clear', handleClear);
    socket.on('whiteboard_restore', handleRestore);
    socket.on('whiteboard_cursor', handleCursor);

    return () => {
      socket.off('whiteboard_patch', handleWhiteboardPatch);
      socket.off('whiteboard_lock_state', handleLockState);
      socket.off('whiteboard_clear', handleClear);
      socket.off('whiteboard_restore', handleRestore);
      socket.off('whiteboard_cursor', handleCursor);
    };
  }, [realtimeClient, isInterviewer, setIsLocked, updateCursor]);

  // 4. Update Readonly state on lock changes
  useEffect(() => {
    if (editorRef.current && !isInterviewer) {
      editorRef.current.updateInstanceState({ isReadonly: isLocked });
    }
  }, [isLocked, isInterviewer]);

  return (
    <div className="w-full h-full relative overflow-hidden bg-slate-950">
      <Tldraw
        onMount={handleMount}
        autoFocus
        hideUi={false}
      />
    </div>
  );
};
