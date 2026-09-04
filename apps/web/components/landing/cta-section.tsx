import React from 'react';
import { ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function CTASection() {
  return (
    <section className="py-24 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/5 to-transparent pointer-events-none" />
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center relative z-10">
        <div className="rounded-3xl border border-primary/20 bg-gradient-to-b from-[#12131c] to-[#0a0a0f] p-8 sm:p-14 shadow-2xl relative overflow-hidden">
          <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-48 bg-primary/20 blur-3xl rounded-full pointer-events-none" />

          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Build better interviews.
          </h2>
          <p className="mt-4 text-base sm:text-lg text-zinc-400 max-w-xl mx-auto">
            Experience the future of technical hiring with zero-install collaborative workspaces,
            isolated Docker execution, and multi-agent AI.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button size="lg" className="w-full sm:w-auto px-8 h-12 shadow-xl shadow-primary/25">
              Create Interview
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="w-full sm:w-auto px-8 h-12 border-zinc-700 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300"
            >
              Explore Platform
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
