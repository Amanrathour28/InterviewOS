'use client';

import React, { useState } from 'react';
import { Download, X, FileText, Table, Check, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api';

interface AnalyticsExportModalProps {
  workspaceId: string;
  isOpen: boolean;
  onClose: () => void;
  defaultWindow?: string;
}

export function AnalyticsExportModal({
  workspaceId,
  isOpen,
  onClose,
  defaultWindow = '30d',
}: AnalyticsExportModalProps) {
  const [exportType, setExportType] = useState<'candidates' | 'interviews' | 'competencies'>('candidates');
  const [format, setFormat] = useState<'csv' | 'json'>('csv');
  const [window, setWindow] = useState(defaultWindow);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleExport = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/analytics/export?workspace_id=${workspaceId}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(localStorage.getItem('interviewos_token')
              ? { Authorization: `Bearer ${localStorage.getItem('interviewos_token')}` }
              : {}),
          },
          body: JSON.stringify({
            export_type: exportType,
            format,
            window,
          }),
        }
      );

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Export failed.');
      }

      if (format === 'csv') {
        const text = await response.text();
        const blob = new Blob([text], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `analytics_${exportType}_${window}_${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        const data = await response.json();
        const jsonStr = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `analytics_${exportType}_${window}_${new Date().toISOString().slice(0, 10)}.json`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }

      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to generate export.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800/80 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Download className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Export Analytics Data</h2>
              <p className="text-xs text-zinc-400">Deterministic export with automated PII sanitization</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <div className="space-y-4 text-xs">
          {/* Export Type */}
          <div className="space-y-1.5">
            <label className="text-zinc-300 font-medium">Dataset Type</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'candidates', label: 'Candidates' },
                { id: 'interviews', label: 'Interviews' },
                { id: 'competencies', label: 'Competencies' },
              ].map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setExportType(t.id as any)}
                  className={`rounded-lg border px-3 py-2 text-center font-medium transition-all ${
                    exportType === t.id
                      ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400'
                      : 'border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Format */}
          <div className="space-y-1.5">
            <label className="text-zinc-300 font-medium">Format</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setFormat('csv')}
                className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-2 text-center font-medium transition-all ${
                  format === 'csv'
                    ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400'
                    : 'border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700'
                }`}
              >
                <Table className="h-4 w-4" />
                CSV (Spreadsheet)
              </button>
              <button
                type="button"
                onClick={() => setFormat('json')}
                className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-2 text-center font-medium transition-all ${
                  format === 'json'
                    ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400'
                    : 'border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700'
                }`}
              >
                <FileText className="h-4 w-4" />
                JSON (Enveloped)
              </button>
            </div>
          </div>

          {/* Time Window */}
          <div className="space-y-1.5">
            <label className="text-zinc-300 font-medium">Time Window</label>
            <select
              value={window}
              onChange={(e) => setWindow(e.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
            >
              <option value="7d">Last 7 Days</option>
              <option value="14d">Last 14 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
              <option value="180d">Last 180 Days</option>
              <option value="365d">Last 365 Days</option>
              <option value="this_quarter">Current Quarter</option>
              <option value="previous_quarter">Previous Quarter</option>
            </select>
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-rose-500/10 border border-rose-500/20 p-2.5 text-rose-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 border-t border-zinc-800/80 pt-4">
          <Button variant="ghost" size="sm" onClick={onClose} className="text-zinc-400 hover:text-white">
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={loading}
            onClick={handleExport}
            className="bg-emerald-600 hover:bg-emerald-500 text-white gap-1.5"
          >
            {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Download {format.toUpperCase()}
          </Button>
        </div>
      </div>
    </div>
  );
}
