import React from 'react';
import { Calendar, UserPlus, Code2, Sparkles, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const steps = [
  {
    step: '01',
    icon: Calendar,
    title: 'Configure & Schedule',
    description:
      'Select job profile, technical difficulty, duration, coding problems, and whiteboard templates. Send instant invites with timezone detection.',
  },
  {
    step: '02',
    icon: UserPlus,
    title: 'Join Real-Time Room',
    description:
      'Candidate and interviewers enter a zero-install, browser-native room with HD WebRTC video, crystal audio, and synchronized workspace.',
  },
  {
    step: '03',
    icon: Code2,
    title: 'Collaborate & Execute Code',
    description:
      'Solve algorithmic and real-world system challenges in Monaco with real-time cursor sync. Validate with sandboxed Docker test runners.',
  },
  {
    step: '04',
    icon: Sparkles,
    title: 'AI Copilot Assistance',
    description:
      'The interviewer receives discreet, context-aware suggestions, topic coverage metrics, and difficulty guidance without candidate awareness.',
  },
  {
    step: '05',
    icon: FileText,
    title: 'Instant Evaluation Report',
    description:
      'Receive a comprehensive candidate scorecard backed by code diffs, run performance, event timeline, and verbatim transcript citations.',
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 bg-background relative overflow-hidden">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <Badge variant="outline" className="mb-3">
            Seamless Workflow
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            From Invitation to Hiring Decision
          </h2>
          <p className="mt-3 text-base text-zinc-400">
            A structured, repeatable process designed to eliminate bias and surface genuine engineering capability.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 relative">
          {steps.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className="flex flex-col items-start p-5 rounded-xl border border-zinc-800/80 bg-zinc-950/40 relative group hover:border-zinc-700 transition-colors"
              >
                <div className="text-2xl font-black text-zinc-700 group-hover:text-primary transition-colors font-mono mb-3">
                  {item.step}
                </div>
                <div className="h-9 w-9 rounded-lg bg-primary-subtle border border-primary/20 flex items-center justify-center text-primary mb-4">
                  <Icon className="h-4 w-4" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">{item.title}</h3>
                <p className="text-xs text-zinc-400 leading-relaxed">{item.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
