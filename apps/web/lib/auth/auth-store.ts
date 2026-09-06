'use client';

import { create } from 'zustand';
import { apiClient, setApiAuthToken, getApiAuthToken } from '@/lib/api';

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name?: string;
  avatar_url?: string;
  role: 'candidate' | 'interviewer' | 'recruiter' | 'organization_admin' | 'platform_admin';
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface WorkspaceSummary {
  id: string;
  name: string;
  slug: string;
  role?: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo_url?: string;
  role?: string;
  workspaces: WorkspaceSummary[];
}

interface AuthState {
  user: User | null;
  token: string | null;
  organizations: Organization[];
  activeOrg: Organization | null;
  activeWorkspace: WorkspaceSummary | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  setAuth: (user: User, token: string) => void;
  loadUser: () => Promise<void>;
  fetchOrganizations: () => Promise<void>;
  setActiveOrg: (org: Organization) => void;
  setActiveWorkspace: (ws: WorkspaceSummary) => void;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  organizations: [],
  activeOrg: null,
  activeWorkspace: null,
  isLoading: true,
  isAuthenticated: false,

  setAuth: (user: User, token: string) => {
    setApiAuthToken(token);
    set({
      user,
      token,
      isAuthenticated: true,
      isLoading: false,
    });
    get().fetchOrganizations();
  },

  loadUser: async () => {
    const token = getApiAuthToken();
    if (!token) {
      set({ isLoading: false, isAuthenticated: false, user: null });
      return;
    }

    try {
      const profile = await apiClient<any>('/auth/me');
      set({
        user: profile,
        isAuthenticated: true,
        isLoading: false,
      });
      await get().fetchOrganizations();
    } catch {
      setApiAuthToken(null);
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },

  fetchOrganizations: async () => {
    try {
      const orgs = await apiClient<Organization[]>('/organizations');
      set({ organizations: orgs });

      const currentActiveOrg = get().activeOrg;
      if (!currentActiveOrg && orgs.length > 0) {
        const defaultOrg = orgs[0];
        const defaultWs = defaultOrg.workspaces?.[0] || null;
        set({
          activeOrg: defaultOrg,
          activeWorkspace: defaultWs,
        });
      }
    } catch {
      // User might not have organizations yet (e.g. newly registered candidate)
    }
  },

  setActiveOrg: (org: Organization) => {
    const defaultWs = org.workspaces?.[0] || null;
    set({
      activeOrg: org,
      activeWorkspace: defaultWs,
    });
  },

  setActiveWorkspace: (ws: WorkspaceSummary) => {
    set({ activeWorkspace: ws });
  },

  logout: async () => {
    try {
      await apiClient('/auth/logout', { method: 'POST' });
    } catch {
      // Ignore network errors during logout
    }
    setApiAuthToken(null);
    set({
      user: null,
      token: null,
      organizations: [],
      activeOrg: null,
      activeWorkspace: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },
}));
