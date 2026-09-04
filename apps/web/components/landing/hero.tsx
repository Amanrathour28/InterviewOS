'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowRight, Sparkles, Play, Code2, ShieldCheck, Cpu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function Hero() {
  return (
    <section className="relative pt-20 pb-16 md:pt-28 md:pb-24 overflow-hidden">
      {/* Glow effect background */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-primary/20 blur-[120px] rounded-full pointer-events-none -z-10" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
        {/* Release / Status Badge */}
        <div className="inline-flex items-center gap-2 mb-6">
          <Badge variant="default" className="py-1 px-3.5 text-xs font-medium border border-primary/30 shadow-inner">
            <Sparkles className="h-3.5 w-3.5 mr-1.5 text-indigo-400" />
            InterviewOS 1.0 • Technical Interview Workspace
          </Badge>
        </div>

        {/* Hero Title */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-[1.1]">
          Where Technical Interviews <br className="hidden sm:inline" />
          <span className="bg-gradient-to-r from-white via-indigo-200 to-indigo-400 bg-clip-text text-transparent">
            Become Intelligent.
          </span>
        </h1>

        {/* Subtitle */}
        <p className="mt-6 text-lg sm:text-xl text-zinc-400 max-w-2xl mx-auto leading-relaxed">
          AI-powered adaptive interviews, collaborative coding, real-time video, 
          system design whiteboarding, and evidence-based candidate evaluation in one unified workspace.
        </p>

        {/* Action Buttons */}
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href="/signup">
            <Button size="lg" className="w-full sm:w-auto text-base px-8 h-12 shadow-xl shadow-primary/25">
              Start Interview
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </Link>
          <Link href="/signup">
            <Button
              variant="secondary"
              size="lg"
              className="w-full sm:w-auto text-base px-8 h-12 border border-zinc-700 bg-zinc-900/90 hover:bg-zinc-800 text-zinc-200"
            >
              <Play className="h-4 w-4 mr-2 text-indigo-400" />
              Try a Mock Interview
            </Button>
          </Link>
        </div>

        {/* Value badges bar */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs sm:text-sm text-zinc-400">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-emerald-400" />
            <span>Multi-Agent AI Copilot</span>
          </div>
          <div className="flex items-center gap-2">
            <Code2 className="h-4 w-4 text-cyan-400" />
            <span>Monaco + Yjs Realtime Sync</span>
          </div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-indigo-400" />
            <span>Isolated Docker Code Execution</span>
          </div>
        </div>
      </div>
    </section>
  );
}
