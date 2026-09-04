'use client';

import React, { useState, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Terminal, Eye, EyeOff, ArrowRight, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { apiClient } from '@/lib/api';
import { useAuthStore } from '@/lib/auth/auth-store';

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background" />}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get('redirect') || '/dashboard';
  const setAuth = useAuthStore((state) => state.setAuth);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const response = await apiClient<any>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email,
          password,
          remember_me: rememberMe,
        }),
      });

      setAuth(response.user, response.access_token);
      router.push(redirectUrl);
    } catch (err: any) {
      setError(err.message || 'Failed to authenticate. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4 bg-background bg-grid-pattern relative">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Logo Header */}
        <div className="flex flex-col items-center text-center space-y-2">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white shadow-lg shadow-primary/30 group-hover:scale-105 transition-transform">
              <Terminal className="h-5 w-5" />
            </div>
            <span className="text-xl font-bold tracking-tight text-white">
              Interview<span className="text-primary font-black">OS</span>
            </span>
          </Link>
          <p className="text-xs text-zinc-400">Sign in to your technical interview workspace</p>
        </div>

        {/* Login Card */}
        <Card className="border-zinc-800 bg-[#0d0e14]/90 backdrop-blur-xl shadow-2xl">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-xl font-bold text-white">Welcome back</CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              Enter your credentials to access your organization and active interviews.
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              {/* Error Alert */}
              {error && (
                <div className="flex items-start gap-2.5 rounded-lg border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300">
                  <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              {/* Email Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Email Address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950/80 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary transition-all"
                />
              </div>

              {/* Password Input */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-zinc-300">Password</label>
                  <Link
                    href="/forgot-password"
                    className="text-[11px] text-primary hover:text-indigo-400 transition-colors"
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950/80 px-3 py-2 pr-10 text-sm text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary transition-all"
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

              {/* Remember session */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="remember"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 rounded border-zinc-800 bg-zinc-900 text-primary focus:ring-primary"
                />
                <label htmlFor="remember" className="text-xs text-zinc-400 cursor-pointer">
                  Remember session for 7 days
                </label>
              </div>
            </CardContent>

            <CardFooter className="flex flex-col gap-3 pt-2">
              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-10 text-sm font-semibold shadow-lg shadow-primary/20"
              >
                {isLoading ? 'Signing in...' : 'Sign In'}
                {!isLoading && <ArrowRight className="h-4 w-4 ml-1.5" />}
              </Button>

              <p className="text-xs text-center text-zinc-400">
                Don&apos;t have an account?{' '}
                <Link href="/signup" className="text-primary hover:underline font-medium">
                  Create account
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
