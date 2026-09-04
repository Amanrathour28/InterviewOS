import React from 'react';
import {
  BrainCircuit,
  Code2,
  Cpu,
  Layout,
  ShieldCheck,
  FileCheck2,
  Lock,
  GitBranch,
  Video,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const features = [
  {
    icon: BrainCircuit,
    title: 'Adaptive AI Interviews',
    badge: 'AI Orchestration',
    badgeVariant: 'default' as const,
    description:
      'Autonomous and AI-assisted interviews that dynamically adjust question depth, probe architectural trade-offs, and assess conceptual reasoning.',
  },
  {
    icon: Code2,
    title: 'Real-Time Collaborative Coding',
    badge: 'Monaco + Yjs',
    badgeVariant: 'accent' as const,
    description:
      'Full-featured code editor with syntax highlighting, language support (Python, Go, Rust, Java, C++, JS/TS), multi-cursor presence, and version snapshots.',
  },
  {
    icon: Cpu,
    title: 'Private AI Copilot for Interviewers',
    badge: 'Real-Time Intelligence',
    badgeVariant: 'warning' as const,
    description:
      'Private sidebar that suggests intelligent follow-ups, analyzes candidate code complexity, and surfaces uncovered competency areas without candidate visibility.',
  },
  {
    icon: Layout,
    title: 'Collaborative System Design Whiteboard',
    badge: 'tldraw Engine',
    badgeVariant: 'success' as const,
    description:
      'Draw architecture diagrams with system components (load balancers, caches, queues, databases) with private interviewer annotation layers.',
  },
  {
    icon: ShieldCheck,
    title: 'Isolated Docker Code Execution',
    badge: 'Zero-Trust Sandbox',
    badgeVariant: 'default' as const,
    description:
      'Untrusted candidate code runs in ephemeral, isolated Docker containers with zero network access, memory caps, CPU quotas, and execution timeouts.',
  },
  {
    icon: FileCheck2,
    title: 'Evidence-Based Candidate Reports',
    badge: 'Objective Rubrics',
    badgeVariant: 'accent' as const,
    description:
      'Detailed hiring recommendations (Strong Hire to No Hire) backed by timeline citations, code snapshots, test outputs, and transcript evidence.',
  },
];

export function Features() {
  return (
    <section id="features" className="py-20 bg-zinc-950/40 border-y border-zinc-900">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <Badge variant="outline" className="mb-3">
            Core Capabilities
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Engineered for High-Stakes Technical Evaluations
          </h2>
          <p className="mt-4 text-base text-zinc-400">
            From coding challenges to distributed system architecture, InterviewOS provides
            specialized tools built specifically for modern technical teams.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, idx) => {
            const Icon = feature.icon;
            return (
              <Card
                key={idx}
                className="bg-[#0f1015]/80 hover:bg-[#14151c] transition-all hover:border-zinc-700 group"
              >
                <CardHeader>
                  <div className="flex items-center justify-between mb-4">
                    <div className="h-10 w-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-105 transition-transform">
                      <Icon className="h-5 w-5" />
                    </div>
                    <Badge variant={feature.badgeVariant} className="text-[11px]">
                      {feature.badge}
                    </Badge>
                  </div>
                  <CardTitle className="text-lg font-bold group-hover:text-indigo-300 transition-colors">
                    {feature.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-zinc-400 text-sm leading-relaxed">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
