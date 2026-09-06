import { create } from 'zustand';
import { WhiteboardData, WhiteboardSnapshotSummary } from '@interviewos/types';

export interface WhiteboardCursor {
  userId: string;
  userName: string;
  userRole: string;
  x: number;
  y: number;
  selectedShapeIds: string[];
}

interface WhiteboardState {
  whiteboard: WhiteboardData | null;
  isLocked: boolean;
  isPrivateLayerOpen: boolean;
  isSnapshotsDrawerOpen: boolean;
  isTemplatesDrawerOpen: boolean;
  isStencilsDrawerOpen: boolean;
  privateNotes: string;
  snapshots: WhiteboardSnapshotSummary[];
  cursors: Record<string, WhiteboardCursor>;

  // Actions
  setWhiteboard: (wb: WhiteboardData | null) => void;
  setIsLocked: (locked: boolean) => void;
  setIsPrivateLayerOpen: (open: boolean) => void;
  setIsSnapshotsDrawerOpen: (open: boolean) => void;
  setIsTemplatesDrawerOpen: (open: boolean) => void;
  setIsStencilsDrawerOpen: (open: boolean) => void;
  setPrivateNotes: (notes: string) => void;
  setSnapshots: (snaps: WhiteboardSnapshotSummary[]) => void;
  addSnapshot: (snap: WhiteboardSnapshotSummary) => void;
  updateCursor: (cursor: WhiteboardCursor) => void;
  removeCursor: (userId: string) => void;
}

export const useWhiteboardStore = create<WhiteboardState>((set) => ({
  whiteboard: null,
  isLocked: false,
  isPrivateLayerOpen: false,
  isSnapshotsDrawerOpen: false,
  isTemplatesDrawerOpen: false,
  isStencilsDrawerOpen: false,
  privateNotes: '',
  snapshots: [],
  cursors: {},

  setWhiteboard: (wb) =>
    set({
      whiteboard: wb,
      isLocked: wb?.is_locked ?? false,
      snapshots: wb?.snapshots ?? [],
      privateNotes: wb?.private_layer?.notes ?? '',
    }),
  setIsLocked: (locked) => set({ isLocked: locked }),
  setIsPrivateLayerOpen: (open) => set({ isPrivateLayerOpen: open }),
  setIsSnapshotsDrawerOpen: (open) => set({ isSnapshotsDrawerOpen: open }),
  setIsTemplatesDrawerOpen: (open) => set({ isTemplatesDrawerOpen: open }),
  setIsStencilsDrawerOpen: (open) => set({ isStencilsDrawerOpen: open }),
  setPrivateNotes: (notes) => set({ privateNotes: notes }),
  setSnapshots: (snaps) => set({ snapshots: snaps }),
  addSnapshot: (snap) => set((state) => ({ snapshots: [snap, ...state.snapshots] })),
  updateCursor: (cursor) =>
    set((state) => ({
      cursors: {
        ...state.cursors,
        [cursor.userId]: cursor,
      },
    })),
  removeCursor: (userId) =>
    set((state) => {
      const next = { ...state.cursors };
      delete next[userId];
      return { cursors: next };
    }),
}));
