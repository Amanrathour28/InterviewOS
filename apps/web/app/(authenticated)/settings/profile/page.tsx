'use client';

import React, { useState, useEffect } from 'react';
import { useAuthStore } from '@/lib/auth/auth-store';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api';
import { CheckCircle2, AlertCircle, User as UserIcon } from 'lucide-react';

export default function ProfileSettingsPage() {
  const { user, loadUser } = useAuthStore();

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (user) {
      setFirstName(user.first_name || '');
      setLastName(user.last_name || '');
      setDisplayName(user.display_name || '');
      setAvatarUrl(user.avatar_url || '');
    }
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setIsSaving(true);

    try {
      await apiClient('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          display_name: displayName.trim() || undefined,
          avatar_url: avatarUrl.trim() || undefined,
        }),
      });
      setSuccess(true);
      await loadUser();
    } catch (err: any) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Profile Settings</h1>
        <p className="text-xs text-zinc-400">
          Manage your personal information and public display preferences.
        </p>
      </div>

      <Card className="border-zinc-800 bg-[#0d0e14]/90">
        <CardHeader className="border-b border-zinc-800/80 pb-4">
          <CardTitle className="text-base font-bold text-white">Personal Information</CardTitle>
          <CardDescription className="text-xs text-zinc-400">
            This information will be displayed to interviewers and candidate panels.
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSave}>
          <CardContent className="space-y-4 pt-4">
            {success && (
              <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-950/30 p-3 text-xs text-emerald-300">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>Profile updated successfully</span>
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300">
                <AlertCircle className="h-4 w-4 text-rose-400" />
                <span>{error}</span>
              </div>
            )}

            {/* Account Metadata Bar */}
            <div className="flex flex-wrap items-center justify-between p-3 rounded-lg bg-zinc-950 border border-zinc-800 text-xs">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center text-primary font-bold text-sm">
                  {firstName[0] || 'U'}
                  {lastName[0] || ''}
                </div>
                <div>
                  <p className="font-semibold text-white">{user?.email}</p>
                  <p className="text-[11px] text-zinc-500">
                    Registered: {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'Active'}
                  </p>
                </div>
              </div>
              <Badge variant="default" className="text-[10px]">
                {user?.role?.replace('_', ' ').toUpperCase()}
              </Badge>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">First Name</label>
                <input
                  type="text"
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Last Name</label>
                <input
                  type="text"
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Display Name (Optional)</label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. Alex M."
                className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Avatar Image URL (Optional)</label>
              <input
                type="url"
                value={avatarUrl}
                onChange={(e) => setAvatarUrl(e.target.value)}
                placeholder="https://images.example.com/avatar.png"
                className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </CardContent>

          <CardFooter className="flex justify-end pt-2 border-t border-zinc-800/80">
            <Button type="submit" disabled={isSaving} className="text-xs font-semibold">
              {isSaving ? 'Saving changes...' : 'Save Profile'}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
