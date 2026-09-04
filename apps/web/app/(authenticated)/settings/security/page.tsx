'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api';
import { CheckCircle2, AlertCircle, Shield, KeyRound, AlertTriangle } from 'lucide-react';

export default function SecuritySettingsPage() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long');
      return;
    }

    setIsUpdating(true);

    try {
      await apiClient('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });

      setSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setError(err.message || 'Failed to update password');
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Security & Sessions</h1>
        <p className="text-xs text-zinc-400">
          Manage your password, authentication sessions, and account protection.
        </p>
      </div>

      {/* Change Password Card */}
      <Card className="border-zinc-800 bg-[#0d0e14]/90">
        <CardHeader className="border-b border-zinc-800/80 pb-4">
          <CardTitle className="text-base font-bold text-white flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-indigo-400" />
            Change Password
          </CardTitle>
          <CardDescription className="text-xs text-zinc-400">
            Ensure your account is using a strong password with letters, numbers, and symbols.
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleChangePassword}>
          <CardContent className="space-y-4 pt-4">
            {success && (
              <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-950/30 p-3 text-xs text-emerald-300">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>Password updated successfully. Other active sessions have been revoked.</span>
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300">
                <AlertCircle className="h-4 w-4 text-rose-400" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Current Password</label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">New Password</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Confirm New Password</label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter new password"
                  className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>
          </CardContent>

          <CardFooter className="flex justify-end pt-2 border-t border-zinc-800/80">
            <Button type="submit" disabled={isUpdating} className="text-xs font-semibold">
              {isUpdating ? 'Updating password...' : 'Update Password'}
            </Button>
          </CardFooter>
        </form>
      </Card>

      {/* Active Sessions Card */}
      <Card className="border-zinc-800 bg-[#0d0e14]/90">
        <CardHeader className="border-b border-zinc-800/80 pb-4">
          <CardTitle className="text-base font-bold text-white flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-400" />
            Session Security
          </CardTitle>
          <CardDescription className="text-xs text-zinc-400">
            Your active sessions use Argon2id password hashing and cryptographic refresh token rotation.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 pt-4 text-xs">
          <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-950 border border-zinc-800">
            <div>
              <p className="font-semibold text-white">Current Browser Session</p>
              <p className="text-[11px] text-zinc-500">Active • Authenticated via short-lived JWT</p>
            </div>
            <Badge variant="success" className="text-[10px]">
              CURRENT
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-rose-950/40 bg-rose-950/10">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-bold text-rose-400 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-400" />
            Danger Zone
          </CardTitle>
          <CardDescription className="text-xs text-zinc-400">
            Deactivating your account will disable your access to organizations and scheduled interviews.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-0">
          <Button variant="outline" className="text-xs border-rose-500/30 text-rose-400 hover:bg-rose-500/10">
            Deactivate Account
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
