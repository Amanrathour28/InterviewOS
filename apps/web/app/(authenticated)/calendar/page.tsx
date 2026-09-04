'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Link from 'next/link';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Clock,
  Globe,
  Users,
  Briefcase,
  ExternalLink,
  AlertCircle,
  CheckCircle2,
  X,
  RotateCw,
  List,
  CalendarDays,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth/auth-store';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface CalendarEvent {
  id: string;
  interview_id: string;
  workspace_id: string;
  title: string;
  candidate_id: string;
  candidate_name?: string;
  candidate_email?: string;
  job_id?: string;
  job_title?: string;
  scheduled_start_at: string;
  scheduled_end_at: string;
  timezone: string;
  status: string;
  interview_status: string;
  interview_type: string;
  duration_minutes: number;
  participant_count: number;
}

const COMMON_TIMEZONES = [
  'UTC',
  'Asia/Kolkata',
  'America/New_York',
  'America/Los_Angeles',
  'America/Chicago',
  'Europe/London',
  'Europe/Berlin',
  'Europe/Paris',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Australia/Sydney',
];

export default function CalendarPage() {
  const { activeWorkspace } = useAuthStore();

  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState<'month' | 'agenda'>('month');
  const [selectedTimezone, setSelectedTimezone] = useState<string>('UTC');
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Event modal state
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [showReschedule, setShowReschedule] = useState(false);
  const [rescheduleDate, setRescheduleDate] = useState('');
  const [rescheduleTime, setRescheduleTime] = useState('10:00');
  const [rescheduleReason, setRescheduleReason] = useState('');
  const [isSubmittingReschedule, setIsSubmittingReschedule] = useState(false);

  // Initialize viewer timezone on mount
  useEffect(() => {
    try {
      const viewerTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (viewerTz) {
        setSelectedTimezone(viewerTz);
      }
    } catch {
      setSelectedTimezone('UTC');
    }
  }, []);

  // Compute month window
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const fetchEvents = useCallback(async () => {
    if (!activeWorkspace) return;
    setIsLoading(true);
    setError(null);

    try {
      // First day of month minus buffer, last day of month plus buffer
      const startWindow = new Date(year, month - 1, 1).toISOString();
      const endWindow = new Date(year, month + 2, 0).toISOString();

      const data = await apiClient<CalendarEvent[]>(
        `/calendar/events?workspace_id=${activeWorkspace.id}&start_date=${encodeURIComponent(startWindow)}&end_date=${encodeURIComponent(endWindow)}`
      );
      setEvents(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load calendar events');
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, year, month]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  // Navigate months
  const handlePrevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const handleNextMonth = () => setCurrentDate(new Date(year, month + 1, 1));
  const handleToday = () => setCurrentDate(new Date());

  // Month grid generation
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDayIndex = new Date(year, month, 1).getDay(); // 0=Sun, 1=Mon, etc.

  // Format date helper in selected timezone
  const formatInTimezone = (dateStr: string, tz: string, format: 'time' | 'full' = 'time') => {
    try {
      const d = new Date(dateStr);
      if (format === 'time') {
        return new Intl.DateTimeFormat('en-US', {
          hour: 'numeric',
          minute: '2-digit',
          timeZone: tz,
        }).format(d);
      }
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        timeZone: tz,
        timeZoneName: 'short',
      }).format(d);
    } catch {
      return dateStr;
    }
  };

  // Group events by day key (YYYY-MM-DD) in the selected timezone
  const eventsByDay = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {};
    for (const ev of events) {
      try {
        const d = new Date(ev.scheduled_start_at);
        // Extract day string in target timezone
        const dayKey = new Intl.DateTimeFormat('en-CA', {
          timeZone: selectedTimezone,
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
        }).format(d);

        if (!map[dayKey]) map[dayKey] = [];
        map[dayKey].push(ev);
      } catch {
        // Fallback
      }
    }
    return map;
  }, [events, selectedTimezone]);

  // Reschedule submit handler
  const handleRescheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEvent || !rescheduleDate || !rescheduleTime) return;

    setIsSubmittingReschedule(true);
    try {
      const combined = `${rescheduleDate}T${rescheduleTime}:00`;
      await apiClient(`/interviews/${selectedEvent.interview_id}/schedule`, {
        method: 'PATCH',
        body: JSON.stringify({
          scheduled_start_at: combined,
          timezone: selectedTimezone,
          reason: rescheduleReason.trim() || undefined,
        }),
      });
      setShowReschedule(false);
      setSelectedEvent(null);
      await fetchEvents();
    } catch (err: any) {
      alert(err.message || 'Failed to reschedule session');
    } finally {
      setIsSubmittingReschedule(false);
    }
  };

  // Cancel submit handler
  const handleCancelSchedule = async (ev: CalendarEvent) => {
    const reason = prompt('Please enter a cancellation reason:');
    if (reason === null) return;

    try {
      await apiClient(`/interviews/${ev.interview_id}/schedule`, {
        method: 'DELETE',
        body: JSON.stringify({ cancellation_reason: reason || 'Cancelled by organizer' }),
      });
      setSelectedEvent(null);
      await fetchEvents();
    } catch (err: any) {
      alert(err.message || 'Failed to cancel schedule');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'confirmed':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'rescheduled':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'cancelled':
        return 'bg-zinc-800 text-zinc-500 border-zinc-700';
      default:
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <CalendarIcon className="h-6 w-6 text-indigo-400" />
            Interview Calendar
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Workspace: <strong className="text-zinc-200">{activeWorkspace?.name || 'Default'}</strong> •{' '}
            {events.length} sessions scheduled
          </p>
        </div>

        {/* View mode toggle & Timezone selector */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Timezone picker */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-zinc-800 bg-zinc-950 text-xs text-zinc-300">
            <Globe className="h-3.5 w-3.5 text-zinc-500" />
            <select
              value={selectedTimezone}
              onChange={(e) => setSelectedTimezone(e.target.value)}
              className="bg-transparent text-xs text-white focus:outline-none cursor-pointer"
            >
              {!COMMON_TIMEZONES.includes(selectedTimezone) && (
                <option value={selectedTimezone}>{selectedTimezone} (Local)</option>
              )}
              {COMMON_TIMEZONES.map((tz) => (
                <option key={tz} value={tz} className="bg-zinc-900 text-white">
                  {tz}
                </option>
              ))}
            </select>
          </div>

          {/* View Mode Buttons */}
          <div className="flex items-center rounded-lg border border-zinc-800 bg-zinc-950 p-0.5">
            <button
              onClick={() => setViewMode('month')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs transition-all ${
                viewMode === 'month' ? 'bg-zinc-800 text-white font-semibold' : 'text-zinc-400 hover:text-white'
              }`}
            >
              <CalendarDays className="h-3.5 w-3.5" />
              Month
            </button>
            <button
              onClick={() => setViewMode('agenda')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs transition-all ${
                viewMode === 'agenda' ? 'bg-zinc-800 text-white font-semibold' : 'text-zinc-400 hover:text-white'
              }`}
            >
              <List className="h-3.5 w-3.5" />
              Agenda
            </button>
          </div>
        </div>
      </div>

      {/* Month Navigation Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-white">
          {currentDate.toLocaleString('en-US', { month: 'long', year: 'numeric' })}
        </h2>

        <div className="flex items-center gap-1.5">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrevMonth}
            className="h-8 w-8 p-0 border-zinc-800 text-zinc-300"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleToday}
            className="h-8 px-2.5 text-xs border-zinc-800 text-zinc-300"
          >
            Today
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleNextMonth}
            className="h-8 w-8 p-0 border-zinc-800 text-zinc-300"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-950/20 text-xs text-rose-400 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* MONTH VIEW GRID */}
      {viewMode === 'month' && (
        <div className="rounded-xl border border-zinc-800 bg-[#0d0e14]/90 overflow-hidden">
          {/* Day of week headers */}
          <div className="grid grid-cols-7 border-b border-zinc-800/80 text-center text-[11px] font-bold text-zinc-400 uppercase py-2 bg-zinc-950">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
              <div key={d}>{d}</div>
            ))}
          </div>

          {/* Days Grid */}
          <div className="grid grid-cols-7 auto-rows-fr divide-x divide-y divide-zinc-800/60 text-xs">
            {/* Empty offset padding for days prior to first of month */}
            {Array.from({ length: firstDayIndex }).map((_, i) => (
              <div key={`empty-${i}`} className="min-h-[100px] p-2 bg-zinc-950/30 text-zinc-700" />
            ))}

            {/* Days in Month */}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const dayNum = i + 1;
              const dateObj = new Date(year, month, dayNum);
              const dayKey = new Intl.DateTimeFormat('en-CA', {
                timeZone: selectedTimezone,
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
              }).format(dateObj);

              const dayEvents = eventsByDay[dayKey] || [];
              const isToday =
                new Date().getDate() === dayNum &&
                new Date().getMonth() === month &&
                new Date().getFullYear() === year;

              return (
                <div
                  key={dayNum}
                  className={`min-h-[100px] p-2 flex flex-col justify-between transition-colors ${
                    isToday ? 'bg-primary/5' : 'hover:bg-zinc-900/30'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span
                      className={`h-5 w-5 rounded-full flex items-center justify-center text-[11px] font-semibold ${
                        isToday ? 'bg-primary text-white font-bold' : 'text-zinc-400'
                      }`}
                    >
                      {dayNum}
                    </span>
                    {dayEvents.length > 0 && (
                      <span className="text-[10px] text-zinc-500 font-mono">
                        {dayEvents.length}
                      </span>
                    )}
                  </div>

                  {/* Event pills */}
                  <div className="space-y-1 overflow-y-auto max-h-[85px]">
                    {dayEvents.map((ev) => (
                      <button
                        key={ev.id}
                        onClick={() => setSelectedEvent(ev)}
                        className={`w-full text-left px-1.5 py-1 rounded text-[11px] font-medium border truncate block transition-all hover:scale-[1.02] ${getStatusColor(
                          ev.status
                        )}`}
                      >
                        <span className="font-bold mr-1">
                          {formatInTimezone(ev.scheduled_start_at, selectedTimezone, 'time')}
                        </span>
                        <span>{ev.candidate_name || ev.title}</span>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* AGENDA / LIST VIEW */}
      {viewMode === 'agenda' && (
        <div className="space-y-3">
          {events.length === 0 ? (
            <Card className="border-zinc-800 bg-[#0d0e14]/90 p-12 text-center text-zinc-500 text-xs">
              No interview sessions scheduled in this window.
            </Card>
          ) : (
            events.map((ev) => (
              <Card
                key={ev.id}
                onClick={() => setSelectedEvent(ev)}
                className="bg-[#0e0f15] border-zinc-800 p-4 hover:border-zinc-700 transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="default" className="text-[10px] uppercase">
                      {ev.interview_type.replace('_', ' ')}
                    </Badge>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase border ${getStatusColor(ev.status)}`}>
                      {ev.status}
                    </span>
                    <span className="text-xs text-zinc-400 font-mono">
                      {formatInTimezone(ev.scheduled_start_at, selectedTimezone, 'full')}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-white">{ev.title}</h3>
                  <div className="flex items-center gap-4 text-xs text-zinc-400">
                    <span>Candidate: <strong className="text-zinc-200">{ev.candidate_name || 'Unassigned'}</strong></span>
                    {ev.job_title && <span>Role: <strong className="text-zinc-200">{ev.job_title}</strong></span>}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500 flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" />
                    {ev.duration_minutes} mins
                  </span>
                  <Button size="sm" variant="outline" className="text-xs border-zinc-800">
                    Details
                  </Button>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* INTERACTIVE EVENT DETAIL MODAL */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-zinc-800 bg-[#0d0e14] p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between border-b border-zinc-800/80 pb-3">
              <div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase border ${getStatusColor(selectedEvent.status)}`}>
                  {selectedEvent.status}
                </span>
                <h3 className="text-lg font-bold text-white mt-1.5">{selectedEvent.title}</h3>
              </div>
              <button onClick={() => setSelectedEvent(null)} className="text-zinc-500 hover:text-white">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1.5">
                <div className="flex items-center justify-between text-zinc-400">
                  <span>Selected Timezone ({selectedTimezone}):</span>
                  <span className="font-bold text-white">
                    {formatInTimezone(selectedEvent.scheduled_start_at, selectedTimezone, 'full')}
                  </span>
                </div>
                <div className="flex items-center justify-between text-zinc-400">
                  <span>Canonical UTC:</span>
                  <span className="font-mono text-zinc-300">
                    {new Date(selectedEvent.scheduled_start_at).toUTCString()}
                  </span>
                </div>
                <div className="flex items-center justify-between text-zinc-400">
                  <span>Original Declared Timezone:</span>
                  <span className="text-indigo-400">{selectedEvent.timezone}</span>
                </div>
                <div className="flex items-center justify-between text-zinc-400">
                  <span>Session Duration:</span>
                  <span className="text-white">{selectedEvent.duration_minutes} minutes</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
                  <span className="text-[10px] font-bold text-zinc-500 uppercase">Candidate</span>
                  <p className="font-bold text-white">{selectedEvent.candidate_name || 'N/A'}</p>
                  <p className="text-[11px] text-zinc-400">{selectedEvent.candidate_email}</p>
                </div>

                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
                  <span className="text-[10px] font-bold text-zinc-500 uppercase">Requisition</span>
                  <p className="font-bold text-white">{selectedEvent.job_title || 'General Screen'}</p>
                  <p className="text-[11px] text-zinc-400">{selectedEvent.participant_count} panel members</p>
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-zinc-800 text-xs">
              <Link href={`/interviews/${selectedEvent.interview_id}`}>
                <Button variant="outline" size="sm" className="text-xs border-zinc-800 text-zinc-300">
                  <ExternalLink className="h-3.5 w-3.5 mr-1" />
                  View Configuration
                </Button>
              </Link>

              <div className="flex items-center gap-2">
                {selectedEvent.status !== 'cancelled' && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowReschedule(true)}
                      className="text-xs border-zinc-800 text-amber-400 hover:bg-amber-500/10"
                    >
                      <RotateCw className="h-3.5 w-3.5 mr-1" />
                      Reschedule
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCancelSchedule(selectedEvent)}
                      className="text-xs border-zinc-800 text-rose-400 hover:bg-rose-500/10"
                    >
                      Cancel
                    </Button>
                  </>
                )}
              </div>
            </div>

            {/* Reschedule inline drawer */}
            {showReschedule && (
              <form onSubmit={handleRescheduleSubmit} className="pt-3 border-t border-zinc-800 space-y-3 text-xs">
                <h4 className="font-bold text-amber-400">Reschedule Session</h4>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-zinc-400">New Date</label>
                    <input
                      type="date"
                      required
                      value={rescheduleDate}
                      onChange={(e) => setRescheduleDate(e.target.value)}
                      className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-zinc-400">New Time</label>
                    <input
                      type="time"
                      required
                      value={rescheduleTime}
                      onChange={(e) => setRescheduleTime(e.target.value)}
                      className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-zinc-400">Reason</label>
                  <input
                    type="text"
                    value={rescheduleReason}
                    onChange={(e) => setRescheduleReason(e.target.value)}
                    placeholder="Candidate requested later slot..."
                    className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowReschedule(false)}
                    className="text-xs"
                  >
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={isSubmittingReschedule} className="text-xs font-semibold">
                    {isSubmittingReschedule ? 'Saving...' : 'Confirm Reschedule'}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
