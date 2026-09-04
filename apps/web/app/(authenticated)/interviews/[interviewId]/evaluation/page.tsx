"use client";

import { use } from "react";
import { EvaluationWorkspace } from "@/components/evaluation/evaluation-workspace";

interface PageProps {
  params: Promise<{
    interviewId: string;
  }>;
}

export default function EvaluationPage({ params }: PageProps) {
  const resolvedParams = use(params);
  return (
    <div className="flex-1 w-full min-h-[calc(100vh-4rem)] p-6 bg-slate-950 text-slate-100">
      <EvaluationWorkspace interviewId={resolvedParams.interviewId} />
    </div>
  );
}
