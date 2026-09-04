'use client';

import React, { useState, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Terminal, Eye, EyeOff, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { apiClient } from '@/lib/api';

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background" />}>
      <ResetPasswordForm />
    </Suspense>
  );
}

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!token) {
      setError('Missing or invalid reset token in URL.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setIsLoading(true);

    try {
      await apiClient('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({
          token,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });
      setIsSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Failed to reset password. The link may have expired.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4 bg-background bg-grid-pattern relative">
      <div className="w-full max-w-md space-y-6">
        <div className="flex flex-col items-center text-center space-y-2">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white">
              <Terminal className="h-5 w-5" />
            </div>
            <span className="text-xl font-bold text-white">InterviewOS</span>
          </Link>
        </div>

        <Card className="border-zinc-800 bg-[#0d0e14]/90 backdrop-blur-xl shadow-2xl">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-xl font-bold text-white">Set New Password</CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              Enter your new account password below.
            </CardDescription>
          </CardHeader>

          {isSuccess ? (
            <CardContent className="space-y-4 pt-2">
              <div className="flex flex-col items-center text-center space-y-3 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <CheckCircle2 className="h-8 w-8 text-emerald-400" />
                <h4 className="text-sm font-semibold text-emerald-300">Password Reset Successfully</h4>
                <p className="text-xs text-zinc-300">
                  Your password has been securely updated and all previous sessions have been revoked.
                </p>
              </div>
              <div className="pt-2">
                <Link href="/login">
                  <Button className="w-full text-xs font-semibold">
                    Sign in with New Password
                  </Button>
                </Link>
              </div>
            </CardContent>
          ) : (
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-4">
                {error && (
                  <div className="flex items-start gap-2.5 rounded-lg border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300">
                    <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-zinc-300">New Password</label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="At least 8 characters"
                      className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950/80 px-3 py-2 pr-10 text-sm text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-zinc-300">Confirm New Password</label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter new password"
                    className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950/80 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </CardContent>

              <CardFooter className="flex flex-col gap-3 pt-2">
                <Button type="submit" disabled={isLoading} className="w-full h-10 text-sm font-semibold">
                  {isLoading ? 'Resetting...' : 'Update Password'}
                </Button>
              </CardFooter>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}
