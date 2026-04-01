import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { LeadCard } from "@/components/LeadCard";
import { toast } from "sonner";
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
  Inbox,
  Clock,
  Trash2,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export function Dashboard({ 
  isRunning, 
  status, 
  results, 
  leadsFromDb, 
  queueStats,
  error, 
  onRunAnalysis, 
  onRetryLeads, 
  jobId, 
  accounts, 
  selectedAccountId, 
  onAccountChange 
}) {
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

  const handleDelete = async (lead) => {
    if (!window.confirm(`Are you sure you want to delete "${lead.name}"? This action cannot be undone.`)) {
      return;
    }
    
    try {
      // Get conversation_id from the lead data (passed from DB)
      const conversationId = lead.conversation_id || lead.profile_url;
      
      if (!conversationId) {
        toast.error("Cannot delete lead: missing conversation ID");
        return;
      }
      
      const response = await fetch(`${API}/leads/${conversationId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const data = await response.json();
      
      if (response.ok) {
        toast.success(`Lead "${lead.name}" deleted`);
        // Reload the page to refresh data
        setTimeout(() => window.location.reload(), 1000);
      } else {
        // Handle HTTP errors
        const errorMsg = data?.detail || data?.message || `HTTP ${response.status}`;
        toast.error(`Failed to delete: ${errorMsg}`);
      }
    } catch (e) {
      // Handle network errors or other exceptions
      console.error('Delete error:', e);
      toast.error(`Failed to delete: ${e.message || 'Network error'}`);
    }
  };
  
  // Only use DB leads - results from job is only for manual analysis progress
  const hasDbLeads = leadsFromDb.length > 0;
  const dbDoneCount = leadsFromDb.filter((l) => l.messages).length || 0;
  const dbPendingCount = queueStats?.pending || 0;
  const totalLeads = status?.total_leads || 0;
  const processed = status?.processed || 0;
  const progressPercent = totalLeads > 0 ? Math.round((processed / totalLeads) * 100) : 0;
  const isComplete = status?.completed;

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
            {queueStats && (
              <div className="flex items-center gap-3 mt-2 text-xs">
                {queueStats.pending > 0 && (
                  <span className="flex items-center gap-1 text-amber-600">
                    <Clock className="h-3.5 w-3.5" />
                    {queueStats.pending} processing
                  </span>
                )}
                {dbDoneCount > 0 && (
                  <span className="flex items-center gap-1 text-emerald-600">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {dbDoneCount} ready
                  </span>
                )}
              </div>
            )}
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

      {/* Unread Leads from DB */}
      {hasDbLeads && !isRunning && (
        <section data-testid="results-section">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-semibold tracking-tight text-[#1a2744]">
              Unread Leads
            </h2>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 text-sm text-slate-500">
                <Inbox className="h-4 w-4" />
                <span>{leadsFromDb.length} total</span>
              </div>
              {dbDoneCount > 0 && (
                <div className="flex items-center gap-1.5 text-sm text-emerald-600">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{dbDoneCount} analyzed</span>
                </div>
              )}
              {dbPendingCount > 0 && (
                <div className="flex items-center gap-1.5 text-sm text-amber-600">
                  <Clock className="h-4 w-4" />
                  <span>{dbPendingCount} processing</span>
                </div>
              )}
              <Button
                onClick={() => window.location.reload()}
                variant="outline"
                size="sm"
                className="h-8"
              >
                <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                Refresh
              </Button>
            </div>
          </div>

          <div className="space-y-4" data-testid="results-list">
            {leadsFromDb.map((lead, idx) => {
              const leadResult = {
                conversation_id: lead.conversation_id,
                name: lead.full_name || "Unknown",
                company: lead.company_name || "",
                position: lead.position || "",
                location: lead.location || "",
                profileUrl: lead.profile_url || "",
                headline: lead.headline || "",
                intent: lead.intent || "",
                intent_confidence: lead.confidence || "",
                status: lead.messages ? "done" : "pending",
                fit_score: lead.analysis?.qualification?.fit_score || 0,
                qualification_status: lead.analysis?.qualification?.status || "",
                executive_summary: lead.executive_summary || "",
                analysis: lead.analysis || {},
                messages: lead.messages?.messages || [],
                recommended_top_3: lead.messages?.recommended_top_3 || [],
                strategy_notes: lead.messages?.notes || "",
              };
              return (
                <LeadCard
                  key={idx}
                  lead={leadResult}
                  index={idx}
                  isSelected={selectedLeads.has(leadResult.name)}
                  onSelect={() => toggleSelect(leadResult.name)}
                  onDelete={handleDelete}
                />
              );
            })}
          </div>
        </section>
      )}

      {/* Empty state when nothing has happened yet */}
      {!isRunning && !status && !results && !hasDbLeads && !error && (
        <div className="text-center py-20" data-testid="empty-state">
          <BarChart3 className="h-16 w-16 text-slate-200 mx-auto mb-6" />
          <h3 className="text-lg font-semibold text-slate-500">Ready to analyze</h3>
          <p className="text-sm text-slate-400 mt-2 max-w-md mx-auto mb-6">
            Leads are automatically analyzed when they reply on LinkedIn.
            Results will appear here instantly.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Button
              onClick={onRunAnalysis}
              disabled={!selectedAccountId}
              className="bg-[#10b981] hover:bg-[#059669] text-white h-12 px-8 text-base font-semibold rounded-lg shadow-sm transition-all active:scale-95 disabled:opacity-60"
              data-testid="run-analysis-btn"
            >
              <Play className="mr-2 h-5 w-5" />
              Run Manual Analysis
            </Button>
          </div>
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
