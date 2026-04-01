import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { LeadCard } from "@/components/LeadCard";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Play,
  Loader2,
  SearchX,
  AlertCircle,
  Users,
  CheckCircle2,
  XCircle,
  BarChart3,
  RefreshCw,
} from "lucide-react";

export function Dashboard({ isRunning, status, results, error, onRunAnalysis, onRetryLeads, jobId, accounts, selectedAccountId, onAccountChange }) {
  const [selectedLeads, setSelectedLeads] = useState(new Set());

  const toggleSelect = (name) => {
    setSelectedLeads((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const handleRetry = () => {
    const names = [...selectedLeads];
    setSelectedLeads(new Set());
    onRetryLeads(names);
  };
  const totalLeads = status?.total_leads || 0;
  const processed = status?.processed || 0;
  const progressPercent = totalLeads > 0 ? Math.round((processed / totalLeads) * 100) : 0;
  const isComplete = status?.completed;
  const hasResults = results?.results?.length > 0;

  const doneCount = results?.results?.filter((r) => r.status === "done").length || 0;
  const failedCount = results?.results?.filter((r) => r.status === "failed").length || 0;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <header className="mb-10" data-testid="app-header">
        <div className="flex items-center justify-between">
          <div>
            <h1
              className="text-3xl font-bold tracking-tight text-[#1a2744]"
              data-testid="app-title"
            >
              Interexy Lead Analyzer
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Automated B2B lead analysis &amp; message generation
            </p>
          </div>
          <Badge
            variant="outline"
            className="text-xs font-mono text-slate-500 border-slate-300"
            data-testid="api-status-badge"
          >
            HeyReach + OpenAI
          </Badge>
        </div>
        <div className="h-px bg-slate-200 mt-6" />
      </header>

      {/* Action Area */}
      <section className="mb-8" data-testid="action-section">
        <div className="flex items-center gap-4">
          {accounts.length > 0 && (
            <Select
              value={selectedAccountId ? String(selectedAccountId) : ""}
              onValueChange={(val) => onAccountChange(Number(val))}
              disabled={isRunning}
            >
              <SelectTrigger className="w-52 h-12 border-slate-300 text-slate-700 font-medium">
                <SelectValue placeholder="Select account..." />
              </SelectTrigger>
              <SelectContent>
                {accounts.map((acc) => (
                  <SelectItem key={acc.id} value={String(acc.id)}>
                    {acc.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button
            onClick={onRunAnalysis}
            disabled={isRunning || !selectedAccountId}
            className="bg-[#10b981] hover:bg-[#059669] text-white h-12 px-8 text-base font-semibold rounded-lg shadow-sm transition-all active:scale-95 disabled:opacity-60"
            data-testid="run-analysis-btn"
          >
            {isRunning ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-5 w-5" />
                Run Analysis
              </>
            )}
          </Button>
          {isRunning && status && (
            <span
              className="text-sm text-slate-500 animate-subtle-pulse"
              data-testid="status-text"
            >
              {status.status_text}
            </span>
          )}
        </div>
      </section>

      {/* Error */}
      {error && (
        <div
          className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3"
          data-testid="error-message"
        >
          <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-800">Analysis Failed</p>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Progress Section */}
      {isRunning && status && status.step !== "done" && (
        <section className="mb-8" data-testid="progress-section">
          <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-[#1a2744] uppercase tracking-wider">
                Progress
              </h3>
              {totalLeads > 0 && (
                <span className="text-sm font-mono text-slate-500">
                  {processed}/{totalLeads} leads
                </span>
              )}
            </div>
            <Progress
              value={totalLeads > 0 ? progressPercent : undefined}
              className="h-2 mb-4"
              data-testid="progress-bar"
            />
            <p className="text-sm text-slate-600" data-testid="progress-status-text">
              {status.status_text}
            </p>

            {/* Per-lead status */}
            {status.leads && status.leads.length > 0 && (
              <div className="mt-4 space-y-2">
                {status.leads.map((lead, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-sm py-1.5 px-3 rounded bg-slate-50"
                    data-testid={`lead-status-${idx}`}
                  >
                    <span className="text-slate-700 font-medium">
                      {lead.name}{" "}
                      <span className="text-slate-400 font-normal">@ {lead.company}</span>
                    </span>
                    <LeadStepBadge step={lead.step} status={lead.status} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      {/* No leads found */}
      {isComplete && totalLeads === 0 && !error && (
        <div
          className="text-center py-16"
          data-testid="no-leads-message"
        >
          <SearchX className="h-12 w-12 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-700">No conversations with recent replies found</h3>
          <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto">
            No unread conversations had a recent reply from your leads.
            Check back later or verify your HeyReach inbox.
          </p>
        </div>
      )}

      {/* Results Summary */}
      {hasResults && (
        <section data-testid="results-section">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-semibold tracking-tight text-[#1a2744]">
              Results
            </h2>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 text-sm text-slate-500">
                <Users className="h-4 w-4" />
                <span>{results.results.length} leads</span>
              </div>
              {doneCount > 0 && (
                <div className="flex items-center gap-1.5 text-sm text-emerald-600">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{doneCount} analyzed</span>
                </div>
              )}
              {failedCount > 0 && (
                <div className="flex items-center gap-1.5 text-sm text-red-500">
                  <XCircle className="h-4 w-4" />
                  <span>{failedCount} failed</span>
                </div>
              )}
              {selectedLeads.size > 0 && (
                <Button
                  onClick={handleRetry}
                  disabled={isRunning}
                  size="sm"
                  className="bg-amber-500 hover:bg-amber-600 text-white font-semibold"
                >
                  <RefreshCw className="mr-1.5 h-4 w-4" />
                  Retry Selected ({selectedLeads.size})
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-4" data-testid="results-list">
            {results.results.map((lead, idx) => (
              <LeadCard
                key={idx}
                lead={lead}
                index={idx}
                jobId={jobId}
                isSelected={selectedLeads.has(lead.name)}
                onSelect={() => toggleSelect(lead.name)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Empty state when nothing has happened yet */}
      {!isRunning && !status && !results && !error && (
        <div className="text-center py-20" data-testid="empty-state">
          <BarChart3 className="h-16 w-16 text-slate-200 mx-auto mb-6" />
          <h3 className="text-lg font-semibold text-slate-500">Ready to analyze</h3>
          <p className="text-sm text-slate-400 mt-2 max-w-md mx-auto">
            Click "Run Analysis" to fetch unread LinkedIn conversations, classify each reply by intent,
            and generate personalized follow-up messages.
          </p>
        </div>
      )}
    </div>
  );
}

function LeadStepBadge({ step, status }) {
  if (status === "done") {
    return (
      <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs">
        Done
      </Badge>
    );
  }
  if (status === "failed") {
    return (
      <Badge className="bg-red-50 text-red-700 border border-red-200 text-xs">
        Failed
      </Badge>
    );
  }

  const stepLabels = {
    waiting: "Waiting",
    analyzing: "Analyzing...",
    generating_messages: "Generating messages...",
  };

  return (
    <Badge className="bg-blue-50 text-blue-700 border border-blue-200 text-xs animate-subtle-pulse">
      {stepLabels[step] || step}
    </Badge>
  );
}
