'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Terminal, ArrowLeft, ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { apiClient } from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await apiClient('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
      setIsSubmitted(true);
    } catch (err: any) {
      setError(err.message || 'Failed to request password reset.');
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
            <CardTitle className="text-xl font-bold text-white">Reset Password</CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              Enter your email address and we&apos;ll send you instructions to reset your password.
            </CardDescription>
          </CardHeader>

          {isSubmitted ? (
            <CardContent className="space-y-4 pt-2">
              <div className="flex flex-col items-center text-center space-y-3 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <CheckCircle2 className="h-8 w-8 text-emerald-400" />
                <h4 className="text-sm font-semibold text-emerald-300">Check your inbox</h4>
                <p className="text-xs text-zinc-300">
                  If an account exists for <span className="font-semibold text-white">{email}</span>, password reset instructions have been generated.
                </p>
                <p className="text-[11px] text-zinc-500">
                  In development mode, check server logs or Mailpit at localhost:8025.
                </p>
              </div>
              <div className="pt-2">
                <Link href="/login">
                  <Button variant="outline" className="w-full text-xs">
                    <ArrowLeft className="h-3.5 w-3.5 mr-2" /> Back to Sign In
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
                  <label className="text-xs font-medium text-zinc-300">Email Address</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950/80 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </CardContent>

              <CardFooter className="flex flex-col gap-3 pt-2">
                <Button type="submit" disabled={isLoading} className="w-full h-10 text-sm font-semibold">
                  {isLoading ? 'Sending instructions...' : 'Send Reset Link'}
                  {!isLoading && <ArrowRight className="h-4 w-4 ml-1.5" />}
                </Button>
                <Link href="/login" className="text-xs text-center text-zinc-400 hover:text-white transition-colors">
                  Return to Sign In
                </Link>
              </CardFooter>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}
