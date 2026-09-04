'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Terminal, Shield, Sparkles, Menu, X, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-zinc-800/80 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-primary text-white shadow-md shadow-primary/20 group-hover:shadow-primary/40 transition-shadow">
            <Terminal className="h-5 w-5" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
            Interview<span className="text-primary font-black">OS</span>
          </span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-zinc-400">
          <Link href="#features" className="hover:text-white transition-colors">
            Features
          </Link>
          <Link href="#preview" className="hover:text-white transition-colors">
            Workspace
          </Link>
          <Link href="#how-it-works" className="hover:text-white transition-colors">
            Workflow
          </Link>
          <Link href="#personas" className="hover:text-white transition-colors">
            Solutions
          </Link>
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/docs`}
            target="_blank"
            rel="noreferrer"
            className="hover:text-white transition-colors flex items-center gap-1"
          >
            API Docs
          </a>
        </nav>

        {/* Action Buttons */}
        <div className="hidden md:flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost" size="sm" className="text-zinc-300 hover:text-white">
              Sign In
            </Button>
          </Link>
          <Link href="/signup">
            <Button size="sm" className="gap-1.5">
              Start Interview
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </Link>
        </div>

        {/* Mobile menu trigger */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden p-2 text-zinc-400 hover:text-white"
        >
          {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile menu dropdown */}
      {mobileOpen && (
        <div className="md:hidden border-b border-zinc-800 bg-background/95 px-4 py-4 space-y-3">
          <Link
            href="#features"
            onClick={() => setMobileOpen(false)}
            className="block py-2 text-sm text-zinc-400 hover:text-white"
          >
            Features
          </Link>
          <Link
            href="#preview"
            onClick={() => setMobileOpen(false)}
            className="block py-2 text-sm text-zinc-400 hover:text-white"
          >
            Workspace Preview
          </Link>
          <Link
            href="#how-it-works"
            onClick={() => setMobileOpen(false)}
            className="block py-2 text-sm text-zinc-400 hover:text-white"
          >
            Workflow
          </Link>
          <Link
            href="#personas"
            onClick={() => setMobileOpen(false)}
            className="block py-2 text-sm text-zinc-400 hover:text-white"
          >
            Solutions
          </Link>
          <div className="pt-2 flex flex-col gap-2">
            <Button variant="outline" size="sm" className="w-full">
              Sign In
            </Button>
            <Button size="sm" className="w-full">
              Start Interview
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}
