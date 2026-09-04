import React from 'react';
import { UserCheck, Building2, CheckCircle2, ArrowRight } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function Personas() {
  return (
    <section id="personas" className="py-20 bg-zinc-950/40 border-t border-zinc-900">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <Badge variant="accent" className="mb-3">
            Tailored Experiences
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Built for Engineers & Talent Teams Alike
          </h2>
          <p className="mt-3 text-base text-zinc-400">
            Whether preparing for your next role or calibrating candidates across dozens of open requisitions.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* For Candidates */}
          <Card className="p-2 bg-[#0c0d12] border-zinc-800">
            <CardHeader className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <UserCheck className="h-5 w-5" />
                </div>
                <div>
                  <Badge variant="accent" className="text-[10px]">For Candidates</Badge>
                  <CardTitle className="text-xl font-bold text-white mt-1">
                    Master Technical Interviews
                  </CardTitle>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-2">
              <p className="text-sm text-zinc-400">
                Sharpen skills with realistic AI-conducted mock interviews, instant code feedback, and deep architectural critiques.
              </p>
              <ul className="space-y-2.5 text-xs sm:text-sm text-zinc-300">
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                  <span>Adaptive mock interviews with realistic follow-up questions</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                  <span>DSA & System Design problem bank with automated verification</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                  <span>Detailed breakdown of time/space complexity and communication clarity</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                  <span>Private practice mode with historical analytics and skill growth curves</span>
                </li>
              </ul>
              <div className="pt-4">
                <Button variant="outline" className="w-full text-xs border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10">
                  Try Candidate Practice
                  <ArrowRight className="h-3.5 w-3.5 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* For Organizations */}
          <Card className="p-2 bg-[#0c0d12] border-zinc-800">
            <CardHeader className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <Badge variant="default" className="text-[10px]">For Organizations</Badge>
                  <CardTitle className="text-xl font-bold text-white mt-1">
                    Scale Objective Engineering Hiring
                  </CardTitle>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-2">
              <p className="text-sm text-zinc-400">
                Standardize technical assessments, equip interviewers with real-time AI assistance, and eliminate hiring ambiguity.
              </p>
              <ul className="space-y-2.5 text-xs sm:text-sm text-zinc-300">
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span>Role-based access control (Candidates, Interviewers, Recruiters, Admins)</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span>Zero-install browser workspace with Monaco, tldraw, and isolated Docker</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span>Private AI copilot for interviewer guidance and uncovered topic probes</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span>Automated evidence-backed scorecards with transcript & code citations</span>
                </li>
              </ul>
              <div className="pt-4">
                <Button className="w-full text-xs">
                  Request Organization Demo
                  <ArrowRight className="h-3.5 w-3.5 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
