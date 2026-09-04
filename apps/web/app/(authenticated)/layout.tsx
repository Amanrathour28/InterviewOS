'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  Terminal,
  Building2,
  ChevronDown,
  Plus,
  LayoutDashboard,
  Users,
  Briefcase,
  Code2,
  Settings,
  LogOut,
  Shield,
  Check,
  Calendar,
  BarChart3,
} from 'lucide-react';
import { AuthGuard } from '@/components/auth/auth-guard';
import { useAuthStore } from '@/lib/auth/auth-store';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <ShellContent>{children}</ShellContent>
    </AuthGuard>
  );
}

function ShellContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, organizations, activeOrg, activeWorkspace, setActiveOrg, setActiveWorkspace, logout } =
    useAuthStore();

  const [orgDropdownOpen, setOrgDropdownOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Jobs', href: '/jobs', icon: Briefcase },
    { name: 'Candidates', href: '/candidates', icon: Users },
    { name: 'Interviews', href: '/interviews', icon: Terminal },
    { name: 'Calendar', href: '/calendar', icon: Calendar },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'Practice', href: '#', icon: Code2, badge: 'Phase 25' },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* Top Header */}
      <header className="sticky top-0 z-40 w-full border-b border-zinc-800 bg-[#09090b]/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-6">
            {/* Logo */}
            <Link href="/dashboard" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white">
                <Terminal className="h-4 w-4" />
              </div>
              <span className="text-base font-bold tracking-tight text-white hidden sm:inline">
                Interview<span className="text-primary font-black">OS</span>
              </span>
            </Link>

            {/* Workspace Switcher */}
            <div className="relative">
              <button
                onClick={() => setOrgDropdownOpen(!orgDropdownOpen)}
                className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-950/70 px-3 py-1.5 text-xs text-zinc-300 hover:border-zinc-700 hover:text-white transition-all"
              >
                <Building2 className="h-3.5 w-3.5 text-indigo-400" />
                <span className="font-semibold text-white max-w-[120px] truncate">
                  {activeOrg?.name || 'Personal Workspace'}
                </span>
                <span className="text-zinc-600">/</span>
                <span className="text-zinc-400 max-w-[100px] truncate">
                  {activeWorkspace?.name || 'Default'}
                </span>
                <ChevronDown className="h-3.5 w-3.5 text-zinc-500 ml-1" />
              </button>

              {/* Dropdown Menu */}
              {orgDropdownOpen && (
                <div className="absolute left-0 mt-2 w-64 rounded-xl border border-zinc-800 bg-[#0d0e14] p-2 shadow-2xl z-50">
                  <div className="px-2 py-1.5 text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
                    Organizations & Workspaces
                  </div>

                  {organizations.length === 0 ? (
                    <div className="p-3 text-xs text-zinc-400 text-center">
                      No organizations yet.
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {organizations.map((org) => (
                        <div key={org.id} className="space-y-0.5">
                          <div
                            onClick={() => {
                              setActiveOrg(org);
                              setOrgDropdownOpen(false);
                            }}
                            className={`flex items-center justify-between px-2 py-1.5 rounded-lg text-xs cursor-pointer ${
                              activeOrg?.id === org.id
                                ? 'bg-primary/15 text-white font-semibold'
                                : 'text-zinc-300 hover:bg-zinc-900'
                            }`}
                          >
                            <span className="truncate">{org.name}</span>
                            {activeOrg?.id === org.id && <Check className="h-3.5 w-3.5 text-primary" />}
                          </div>

                          {/* Workspaces list under selected org */}
                          {activeOrg?.id === org.id && (
                            <div className="pl-4 space-y-0.5 pt-0.5">
                              {org.workspaces.map((ws) => (
                                <div
                                  key={ws.id}
                                  onClick={() => {
                                    setActiveWorkspace(ws);
                                    setOrgDropdownOpen(false);
                                  }}
                                  className={`flex items-center justify-between px-2 py-1 rounded text-[11px] cursor-pointer ${
                                    activeWorkspace?.id === ws.id
                                      ? 'text-indigo-400 font-medium'
                                      : 'text-zinc-400 hover:text-white'
                                  }`}
                                >
                                  <span>{ws.name}</span>
                                  {activeWorkspace?.id === ws.id && (
                                    <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-2 pt-2 border-t border-zinc-800/80">
                    <Link
                      href="/onboarding"
                      onClick={() => setOrgDropdownOpen(false)}
                      className="flex items-center gap-1.5 px-2 py-1.5 text-xs text-primary hover:text-indigo-300 font-medium transition-colors"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Create Organization
                    </Link>
                  </div>
                </div>
              )}
            </div>

            {/* Navigation links */}
            <nav className="hidden md:flex items-center gap-1 text-xs font-medium">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-zinc-800 text-white font-semibold'
                        : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60'
                    }`}
                  >
                    <item.icon className="h-3.5 w-3.5" />
                    <span>{item.name}</span>
                    {item.badge && (
                      <span className="text-[10px] text-zinc-500 bg-zinc-900 border border-zinc-800 px-1.5 py-0.2 rounded">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Right: User Menu */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2.5 p-1 rounded-lg hover:bg-zinc-900 transition-colors"
              >
                <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-indigo-500 to-primary text-white font-bold text-xs flex items-center justify-center uppercase shadow-sm">
                  {user?.first_name?.[0] || 'U'}
                  {user?.last_name?.[0] || ''}
                </div>
                <div className="hidden lg:flex flex-col text-left">
                  <span className="text-xs font-semibold text-white leading-tight">
                    {user?.display_name || user?.first_name || 'User'}
                  </span>
                  <span className="text-[10px] text-zinc-400 capitalize">{user?.role?.replace('_', ' ') || 'Candidate'}</span>
                </div>
                <ChevronDown className="h-3.5 w-3.5 text-zinc-500 hidden sm:block" />
              </button>

              {/* User Dropdown */}
              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-56 rounded-xl border border-zinc-800 bg-[#0d0e14] p-2 shadow-2xl z-50 space-y-1">
                  <div className="px-3 py-2 border-b border-zinc-800/80 mb-1">
                    <p className="text-xs font-semibold text-white">{user?.first_name} {user?.last_name}</p>
                    <p className="text-[11px] text-zinc-400 truncate">{user?.email}</p>
                    <div className="mt-1.5">
                      <Badge variant="default" className="text-[10px]">
                        {user?.role?.replace('_', ' ').toUpperCase()}
                      </Badge>
                    </div>
                  </div>

                  <Link
                    href="/settings/profile"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-xs text-zinc-300 hover:text-white hover:bg-zinc-900 rounded-lg transition-colors"
                  >
                    <Settings className="h-3.5 w-3.5 text-zinc-400" />
                    Profile & Settings
                  </Link>

                  <Link
                    href="/settings/security"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-xs text-zinc-300 hover:text-white hover:bg-zinc-900 rounded-lg transition-colors"
                  >
                    <Shield className="h-3.5 w-3.5 text-zinc-400" />
                    Security & Sessions
                  </Link>

                  <div className="pt-1 border-t border-zinc-800/80">
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
