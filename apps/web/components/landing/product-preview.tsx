'use client';

import React, { useState } from 'react';
import {
  Code2,
  Cpu,
  Layout,
  Video,
  Play,
  CheckCircle2,
  Clock,
  Mic,
  MicOff,
  VideoIcon,
  Share2,
  Sparkles,
  Layers,
  Terminal,
  ChevronRight,
  ShieldAlert,
  User,
  Activity,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export function ProductPreview() {
  const [activeTab, setActiveTab] = useState<'code' | 'copilot' | 'whiteboard' | 'video'>('code');
  const [isRunningCode, setIsRunningCode] = useState(false);
  const [codeOutput, setCodeOutput] = useState<string | null>(null);

  const handleRunCode = () => {
    setIsRunningCode(true);
    setTimeout(() => {
      setIsRunningCode(false);
      setCodeOutput(`[Sandbox Worker #284] Running isolated Docker container...
✓ Test 1: test_get_existing_key (0.4ms) - PASSED
✓ Test 2: test_put_capacity_eviction (0.8ms) - PASSED
✓ Test 3: test_concurrent_access (1.2ms) - PASSED
-------------------------------------------------------
Ran 3 tests in 0.014s (Memory: 18.4MB / 256MB)
Status: SUCCESS (3/3 public test cases passed)`);
    }, 600);
  };

  return (
    <section id="preview" className="relative py-12 md:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-10">
          <Badge variant="accent" className="mb-3">
            Interactive Workspace
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            One Unified Workspace for the Entire Interview
          </h2>
          <p className="mt-3 text-base text-zinc-400 max-w-xl mx-auto">
            Switch seamlessly between collaborative coding, private AI interviewer assistance,
            distributed system whiteboarding, and video feeds.
          </p>
        </div>

        {/* Mock Window Container */}
        <div className="rounded-2xl border border-zinc-800 bg-[#0c0d12] shadow-2xl overflow-hidden">
          {/* Top Interview Header Bar */}
          <div className="flex flex-wrap items-center justify-between border-b border-zinc-800/80 bg-zinc-950/80 px-4 py-3 gap-3">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="h-3 w-3 rounded-full bg-rose-500/80 inline-block" />
                <span className="h-3 w-3 rounded-full bg-amber-500/80 inline-block" />
                <span className="h-3 w-3 rounded-full bg-emerald-500/80 inline-block" />
              </div>
              <div className="h-4 w-px bg-zinc-800 mx-1 hidden sm:block" />
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                  Staff Systems Engineer
                </span>
                <span className="text-zinc-600">•</span>
                <span className="text-xs text-zinc-300 font-medium">Candidate: Alex Morgan</span>
              </div>
            </div>

            {/* Live Indicator & Timer */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 rounded-full bg-zinc-900 border border-zinc-800 px-3 py-1 text-xs text-zinc-300">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-mono text-emerald-400 font-semibold">LIVE</span>
                <span className="text-zinc-600">|</span>
                <Clock className="h-3.5 w-3.5 text-zinc-400" />
                <span className="font-mono">00:38:42</span>
              </div>
              <Badge variant="outline" className="text-xs border-zinc-700 text-zinc-400 hidden sm:inline-flex">
                Docker Sandbox: Active
              </Badge>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex items-center border-b border-zinc-800 bg-zinc-900/60 px-4 overflow-x-auto">
            <button
              onClick={() => setActiveTab('code')}
              className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs sm:text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === 'code'
                  ? 'border-primary text-white bg-zinc-800/40'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Code2 className="h-4 w-4 text-indigo-400" />
              Collaborative Code (Monaco)
            </button>
            <button
              onClick={() => setActiveTab('copilot')}
              className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs sm:text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === 'copilot'
                  ? 'border-primary text-white bg-zinc-800/40'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Cpu className="h-4 w-4 text-cyan-400" />
              AI Copilot (Private Interviewer View)
            </button>
            <button
              onClick={() => setActiveTab('whiteboard')}
              className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs sm:text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === 'whiteboard'
                  ? 'border-primary text-white bg-zinc-800/40'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Layout className="h-4 w-4 text-emerald-400" />
              System Architecture Whiteboard
            </button>
            <button
              onClick={() => setActiveTab('video')}
              className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs sm:text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === 'video'
                  ? 'border-primary text-white bg-zinc-800/40'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Video className="h-4 w-4 text-amber-400" />
              WebRTC Video & Audio
            </button>
          </div>

          {/* Main Tab Content Display */}
          <div className="min-h-[460px] p-4 sm:p-6 font-mono text-xs sm:text-sm text-zinc-300">
            {/* TAB 1: CODE EDITOR */}
            {activeTab === 'code' && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-full">
                {/* Editor Area (8 cols) */}
                <div className="lg:col-span-8 flex flex-col rounded-xl border border-zinc-800/80 bg-[#0f1015] overflow-hidden">
                  <div className="flex items-center justify-between border-b border-zinc-800/80 bg-zinc-950/60 px-4 py-2">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-indigo-300">
                        solution.py
                      </span>
                      <span className="text-xs text-zinc-500">Python 3.10 • Yjs Synced</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                        <User className="h-3 w-3" /> Candidate editing
                      </div>
                      <Button
                        size="sm"
                        onClick={handleRunCode}
                        disabled={isRunningCode}
                        className="h-7 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-500 border-none shadow-none text-white"
                      >
                        <Play className="h-3 w-3 fill-current" />
                        {isRunningCode ? 'Running Sandbox...' : 'Run Code'}
                      </Button>
                    </div>
                  </div>

                  {/* Code Body */}
                  <div className="p-4 space-y-1 font-mono text-xs sm:text-sm overflow-x-auto leading-relaxed">
                    <p className="text-zinc-500"># Implement an LRU Cache with O(1) get and put complexity</p>
                    <p><span className="text-purple-400">class</span> <span className="text-amber-300">Node</span>:</p>
                    <p className="pl-4"><span className="text-purple-400">def</span> <span className="text-blue-400">__init__</span>(<span className="text-zinc-400">self, key, val</span>):</p>
                    <p className="pl-8"><span className="text-zinc-400">self.key, self.val = key, val</span></p>
                    <p className="pl-8"><span className="text-zinc-400">self.prev = self.next = </span><span className="text-purple-400">None</span></p>
                    <br />
                    <p><span className="text-purple-400">class</span> <span className="text-amber-300">LRUCache</span>:</p>
                    <p className="pl-4"><span className="text-purple-400">def</span> <span className="text-blue-400">__init__</span>(<span className="text-zinc-400">self, capacity: int</span>):</p>
                    <p className="pl-8"><span className="text-zinc-400">self.cap = capacity</span></p>
                    <p className="pl-8"><span className="text-zinc-400">self.cache = {} </span><span className="text-zinc-500"># key to node</span></p>
                    <p className="pl-8 relative inline-block">
                      <span className="text-zinc-400">self.head, self.tail = Node(0, 0), Node(0, 0)</span>
                      {/* Live Cursor Indicator */}
                      <span className="absolute -top-3 right-0 bg-indigo-600 text-[10px] text-white px-1 rounded-t">
                        Alex (Candidate)
                      </span>
                    </p>
                    <p className="pl-8"><span className="text-zinc-400">self.head.next = self.tail</span></p>
                    <p className="pl-8"><span className="text-zinc-400">self.tail.prev = self.head</span></p>
                  </div>

                  {/* Terminal Execution Output */}
                  <div className="mt-auto border-t border-zinc-800 bg-black/70 p-3">
                    <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
                      <span className="flex items-center gap-1">
                        <Terminal className="h-3.5 w-3.5 text-zinc-500" /> Output Console
                      </span>
                      <span className="text-[11px] text-zinc-500">Isolated Worker Sandbox (0.1ms ping)</span>
                    </div>
                    <pre className="text-xs text-emerald-400 whitespace-pre-wrap">
                      {codeOutput || `Click "Run Code" above to execute test cases against isolated Docker sandbox.`}
                    </pre>
                  </div>
                </div>

                {/* Problem Description & Hidden Tests (4 cols) */}
                <div className="lg:col-span-4 flex flex-col gap-4">
                  <div className="rounded-xl border border-zinc-800/80 bg-[#0f1015] p-4">
                    <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                      <Layers className="h-4 w-4 text-indigo-400" /> Problem: Design LRU Cache
                    </h4>
                    <p className="text-xs text-zinc-400 leading-relaxed">
                      Design a data structure that follows the constraints of a Least Recently Used (LRU) cache.
                      Functions <code className="text-indigo-300">get</code> and <code className="text-indigo-300">put</code> must each run in <code className="text-emerald-400">O(1)</code> average time complexity.
                    </p>
                  </div>

                  <div className="rounded-xl border border-zinc-800/80 bg-[#0f1015] p-4 flex-1">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-semibold text-zinc-300">Test Cases</span>
                      <Badge variant="outline" className="text-[10px]">3 Public / 4 Hidden</Badge>
                    </div>
                    <div className="space-y-2 text-xs">
                      <div className="p-2 rounded bg-zinc-900/80 border border-zinc-800 flex items-center justify-between">
                        <span className="text-zinc-300">Test 1: Simple put & get</span>
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      </div>
                      <div className="p-2 rounded bg-zinc-900/80 border border-zinc-800 flex items-center justify-between">
                        <span className="text-zinc-300">Test 2: Capacity eviction</span>
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      </div>
                      <div className="p-2 rounded bg-zinc-900/80 border border-zinc-800 flex items-center justify-between">
                        <span className="text-zinc-300">Test 3: Update existing key</span>
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      </div>
                      <div className="p-2 rounded bg-zinc-950/50 border border-dashed border-zinc-800 text-zinc-500 text-[11px] flex items-center gap-1.5">
                        <ShieldAlert className="h-3.5 w-3.5 text-zinc-500" /> 4 Hidden tests run after submission
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: AI COPILOT */}
            {activeTab === 'copilot' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-xl border border-zinc-800 bg-[#0f1015] p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold text-white flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-cyan-400" />
                      Live AI Interviewer Suggestions
                    </h4>
                    <span className="text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                      Interviewer Only • Hidden from Candidate
                    </span>
                  </div>

                  {/* Suggestion Card 1 */}
                  <div className="rounded-lg border border-cyan-500/30 bg-cyan-950/20 p-4 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-cyan-300">Recommended Follow-up</span>
                      <span className="text-zinc-400 text-[11px]">Based on code in solution.py</span>
                    </div>
                    <p className="text-xs text-zinc-200 font-sans">
                      &quot;The candidate implemented doubly-linked list without locks. Ask: <strong>&apos;How would you make this LRU cache thread-safe under high concurrent read/write throughput?&apos;</strong>&quot;
                    </p>
                    <div className="flex gap-2 pt-1">
                      <Button size="sm" variant="subtle" className="h-6 text-[11px]">Ask Question</Button>
                      <Button size="sm" variant="ghost" className="h-6 text-[11px]">Skip</Button>
                    </div>
                  </div>

                  {/* Suggestion Card 2 */}
                  <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-indigo-300">Time & Space Analysis</span>
                      <span className="text-emerald-400 text-[11px]">Optimal O(1) Achieved</span>
                    </div>
                    <p className="text-xs text-zinc-300 font-sans">
                      Candidate correctly avoided array lookups by pairing the dictionary with a doubly linked list. Space complexity is O(Capacity).
                    </p>
                  </div>
                </div>

                {/* Candidate Competency Matrix */}
                <div className="rounded-xl border border-zinc-800 bg-[#0f1015] p-5 space-y-4">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <Activity className="h-4 w-4 text-emerald-400" /> Real-time Evaluation Signals
                  </h4>
                  <div className="space-y-3 font-sans">
                    <div>
                      <div className="flex justify-between text-xs text-zinc-300 mb-1">
                        <span>Data Structures & Algorithms</span>
                        <span className="text-emerald-400 font-bold">92%</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                        <div className="h-full bg-emerald-500 rounded-full w-[92%]" />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-xs text-zinc-300 mb-1">
                        <span>Code Cleanliness & Modular Design</span>
                        <span className="text-indigo-400 font-bold">88%</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                        <div className="h-full bg-indigo-500 rounded-full w-[88%]" />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-xs text-zinc-300 mb-1">
                        <span>Problem Communication</span>
                        <span className="text-cyan-400 font-bold">85%</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                        <div className="h-full bg-cyan-500 rounded-full w-[85%]" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: WHITEBOARD */}
            {activeTab === 'whiteboard' && (
              <div className="rounded-xl border border-zinc-800 bg-[#0d0e14] p-6 text-center">
                <div className="flex items-center justify-between mb-4 border-b border-zinc-800 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white">System Architecture Canvas (tldraw)</span>
                    <Badge variant="accent" className="text-[10px]">Shared Layer</Badge>
                  </div>
                  <span className="text-xs text-zinc-400">Real-time CRDT Sync</span>
                </div>
                {/* Visual Architecture Diagram Representation */}
                <div className="p-8 rounded-lg bg-zinc-950/80 border border-zinc-800/80 flex flex-wrap items-center justify-center gap-6 font-sans">
                  <div className="p-4 rounded-lg bg-zinc-900 border border-indigo-500/50 shadow-lg text-xs">
                    <div className="font-bold text-white">Client App</div>
                    <div className="text-[11px] text-zinc-400">Web / Mobile</div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-zinc-600 hidden sm:block" />
                  <div className="p-4 rounded-lg bg-zinc-900 border border-cyan-500/50 shadow-lg text-xs">
                    <div className="font-bold text-white">Cloudflare / NGINX</div>
                    <div className="text-[11px] text-zinc-400">Edge Rate Limiter</div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-zinc-600 hidden sm:block" />
                  <div className="p-4 rounded-lg bg-zinc-900 border border-emerald-500/50 shadow-lg text-xs">
                    <div className="font-bold text-white">API Gateway</div>
                    <div className="text-[11px] text-zinc-400">JWT Auth & Routing</div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-zinc-600 hidden sm:block" />
                  <div className="p-4 rounded-lg bg-zinc-900 border border-amber-500/50 shadow-lg text-xs">
                    <div className="font-bold text-white">Postgres + Redis</div>
                    <div className="text-[11px] text-zinc-400">Read Replica Cluster</div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 4: VIDEO & AUDIO */}
            {activeTab === 'video' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-xl border border-zinc-800 bg-zinc-950 relative h-64 flex flex-col justify-between p-4 overflow-hidden">
                  <div className="flex justify-between items-center z-10">
                    <span className="bg-black/60 backdrop-blur px-2.5 py-1 rounded text-xs text-white">
                      Alex Morgan (Candidate)
                    </span>
                    <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  </div>
                  <div className="self-center text-zinc-600 text-sm flex flex-col items-center gap-2">
                    <div className="w-16 h-16 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-300 font-bold text-xl">
                      AM
                    </div>
                    <span>HD 1080p WebRTC Stream</span>
                  </div>
                  <div className="z-10 bg-black/60 backdrop-blur p-2 rounded text-[11px] text-zinc-300">
                    <span className="text-indigo-400 font-semibold">Transcript:</span> &quot;I chose the doubly-linked list so that removing an arbitrary node upon eviction takes O(1)...&quot;
                  </div>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-950 relative h-64 flex flex-col justify-between p-4 overflow-hidden">
                  <div className="flex justify-between items-center z-10">
                    <span className="bg-black/60 backdrop-blur px-2.5 py-1 rounded text-xs text-white">
                      Marcus Vance (Interviewer)
                    </span>
                    <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  </div>
                  <div className="self-center text-zinc-600 text-sm flex flex-col items-center gap-2">
                    <div className="w-16 h-16 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-300 font-bold text-xl">
                      MV
                    </div>
                    <span>HD 1080p WebRTC Stream</span>
                  </div>
                  <div className="z-10 bg-black/60 backdrop-blur p-2 rounded text-[11px] text-zinc-300">
                    <span className="text-cyan-400 font-semibold">Transcript:</span> &quot;Makes sense. Let&apos;s talk about what happens when multiple worker threads write simultaneously.&quot;
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Bottom Meeting Control Bar */}
          <div className="border-t border-zinc-800 bg-zinc-950/90 px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <button className="p-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-300 transition-colors">
                <Mic className="h-4 w-4" />
              </button>
              <button className="p-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-300 transition-colors">
                <VideoIcon className="h-4 w-4" />
              </button>
              <button className="p-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-300 transition-colors">
                <Share2 className="h-4 w-4" />
              </button>
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="destructive" className="h-8 text-xs font-semibold">
                End Interview
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
