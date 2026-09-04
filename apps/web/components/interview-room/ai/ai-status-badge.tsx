'use client';

import React, { useEffect, useState } from 'react';
import { Sparkles, CheckCircle2, AlertTriangle, Cpu } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { useAIStore } from '@/lib/stores/use-ai-store';
import { aiApi } from '@/lib/api/ai';

export const AIStatusBadge: React.FC<{ onClick?: () => void }> = ({ onClick }) => {
  const { lastMetadata, isLoading } = useAIStore();
  const [health, setHealth] = useState<{ status: string; service: string; providers?: any } | null>(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const data = await aiApi.getHealth();
        if (mounted) setHealth(data);
      } catch {
        if (mounted) setHealth({ status: 'offline', service: 'ai-gateway' });
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const isFallback = lastMetadata?.is_fallback;
  const isHealthy = health?.status === 'ok' || health?.status === 'healthy';

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-150 border hover:opacity-90 focus:outline-none focus:ring-1 focus:ring-violet-500 bg-slate-900/80 backdrop-blur border-slate-800 text-slate-200"
      title={
        isFallback
          ? 'AI fallback provider active (local LLM)'
          : lastMetadata
          ? `Provider: ${lastMetadata.provider} | Model: ${lastMetadata.model} | Latency: ${lastMetadata.latency_ms}ms`
          : 'AI Copilot Ready'
      }
    >
      <Sparkles className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-violet-400' : 'text-violet-400'}`} />
      <span className="font-semibold tracking-wide">AI Copilot</span>

      {isLoading ? (
        <span className="text-[10px] text-violet-300 font-mono animate-pulse">thinking...</span>
      ) : isFallback ? (
        <Badge variant="outline" className="h-4 px-1 text-[9px] bg-amber-500/20 text-amber-300 border-amber-500/40">
          <AlertTriangle className="w-2.5 h-2.5 mr-0.5" /> fallback
        </Badge>
      ) : lastMetadata?.model ? (
        <Badge variant="outline" className="h-4 px-1 text-[9px] bg-violet-500/10 text-violet-300 border-violet-500/30">
          <Cpu className="w-2.5 h-2.5 mr-0.5" /> {lastMetadata.provider}
        </Badge>
      ) : (
        <span className={`w-1.5 h-1.5 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-amber-400'}`} />
      )}
    </button>
  );
};
