import React from 'react';
import Link from 'next/link';
import { Terminal, Github } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-t border-zinc-800/80 bg-zinc-950 text-zinc-400 text-xs sm:text-sm">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
          {/* Col 1: Brand */}
          <div className="col-span-2 space-y-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded bg-primary text-white">
                <Terminal className="h-4 w-4" />
              </div>
              <span className="text-base font-bold text-white tracking-tight">
                Interview<span className="text-primary">OS</span>
              </span>
            </Link>
            <p className="text-xs text-zinc-500 max-w-xs leading-relaxed">
              Production-level AI interview, collaborative coding, and candidate evaluation platform.
            </p>
            <div className="flex items-center gap-3 pt-2 text-zinc-400">
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="hover:text-white transition-colors"
              >
                <Github className="h-4 w-4" />
              </a>
            </div>
          </div>

          {/* Col 2: Product */}
          <div className="space-y-2.5">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">Product</h4>
            <ul className="space-y-2 text-xs">
              <li><Link href="#preview" className="hover:text-white transition-colors">Workspace</Link></li>
              <li><Link href="#features" className="hover:text-white transition-colors">AI Copilot</Link></li>
              <li><Link href="#features" className="hover:text-white transition-colors">Monaco Code Editor</Link></li>
              <li><Link href="#features" className="hover:text-white transition-colors">Whiteboard (tldraw)</Link></li>
              <li><Link href="#features" className="hover:text-white transition-colors">Docker Sandbox</Link></li>
            </ul>
          </div>

          {/* Col 3: Developers & Docs */}
          <div className="space-y-2.5">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">Developers</h4>
            <ul className="space-y-2 text-xs">
              <li><a href="http://localhost:8000/api/v1/docs" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">FastAPI Swagger</a></li>
              <li><a href="http://localhost:8000/api/v1/health" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">Health Telemetry</a></li>
              <li><Link href="#how-it-works" className="hover:text-white transition-colors">Architecture</Link></li>
              <li><a href="#" className="hover:text-white transition-colors">Security & Isolation</a></li>
            </ul>
          </div>

          {/* Col 4: Legal & Security */}
          <div className="space-y-2.5">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">Security & Legal</h4>
            <ul className="space-y-2 text-xs">
              <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Zero-Trust Sandbox</a></li>
              <li><a href="#" className="hover:text-white transition-colors">RBAC Enforcement</a></li>
            </ul>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-zinc-800/60 flex flex-col sm:flex-row items-center justify-between text-xs text-zinc-500 gap-4">
          <p>© {new Date().getFullYear()} InterviewOS Platform. Built for production-grade technical hiring.</p>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block" />
              All Systems Operational
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
