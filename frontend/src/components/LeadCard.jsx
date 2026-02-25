import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  ChevronDown,
  ChevronUp,
  MapPin,
  Building2,
  Briefcase,
  Copy,
  Check,
  Star,
  ExternalLink,
  AlertCircle,
} from "lucide-react";
import { MessageGroup } from "@/components/MessageGroup";

export function LeadCard({ lead, index }) {
  const [expanded, setExpanded] = useState(false);

  if (lead.status === "failed") {
    return (
      <div
        className="bg-white rounded-lg border border-red-200 shadow-sm p-5"
        data-testid={`lead-card-${index}`}
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              {lead.name || "Unknown Lead"}
              {lead.company && (
                <span className="text-slate-400 font-normal ml-2">@ {lead.company}</span>
              )}
            </h3>
            <p className="text-sm text-red-600 mt-1">
              Analysis failed: {lead.error || "Unknown error"}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const fitScore = lead.fit_score || 0;

  return (
    <div
      className="bg-white rounded-lg border border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden"
      data-testid={`lead-card-${index}`}
    >
      {/* Card Header - always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-5 text-left flex items-center justify-between hover:bg-slate-50/50 transition-colors"
        data-testid={`lead-card-toggle-${index}`}
      >
        <div className="flex items-center gap-4 min-w-0">
          {/* Fit Score */}
          <FitScoreBadge score={fitScore} />

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-[#1a2744] truncate">
                {lead.name}
              </h3>
              {lead.profileUrl && (
                <a
                  href={lead.profileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-slate-400 hover:text-[#1a2744] transition-colors"
                  data-testid={`lead-linkedin-link-${index}`}
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </div>
            <div className="flex items-center gap-3 text-sm text-slate-500 mt-0.5 flex-wrap">
              {lead.position && (
                <span className="flex items-center gap-1">
                  <Briefcase className="h-3.5 w-3.5" />
                  {lead.position}
                </span>
              )}
              {lead.company && (
                <span className="flex items-center gap-1">
                  <Building2 className="h-3.5 w-3.5" />
                  {lead.company}
                </span>
              )}
              {lead.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5" />
                  {lead.location}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0 ml-4">
          {lead.messages?.length > 0 && (
            <span className="text-xs text-slate-400">
              {lead.messages.length} messages
            </span>
          )}
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-slate-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-slate-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-slate-100 px-5 pb-5" data-testid={`lead-card-content-${index}`}>
          {/* Executive Summary */}
          {lead.executive_summary && (
            <div className="mt-4 mb-5">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Executive Summary
              </h4>
              <p className="text-sm leading-relaxed text-slate-700" data-testid={`lead-summary-${index}`}>
                {lead.executive_summary}
              </p>
            </div>
          )}

          {/* Qualification Details */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            <MetricCard label="Fit Score" value={`${fitScore}/10`} />
            <MetricCard label="Status" value={lead.qualification_status || "N/A"} />
            <MetricCard
              label="Authority"
              value={lead.analysis?.qualification?.authority_level || "N/A"}
            />
            <MetricCard
              label="Urgency"
              value={lead.analysis?.qualification?.need_urgency || "N/A"}
            />
          </div>

          {/* Recommended Top 3 Messages */}
          {lead.recommended_top_3?.length > 0 && lead.messages?.length > 0 && (
            <div className="mb-5">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Star className="h-3.5 w-3.5 text-amber-500" />
                Top Recommended Messages
              </h4>
              <div className="space-y-2">
                {lead.recommended_top_3.map((msgId) => {
                  const msg = lead.messages.find((m) => m.id === msgId);
                  if (!msg) return null;
                  return (
                    <MessageCard
                      key={msgId}
                      message={msg}
                      highlighted
                      testIdPrefix={`lead-${index}-top`}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {/* All Messages Grouped by Type */}
          {lead.messages?.length > 0 && (
            <MessageGroup messages={lead.messages} leadIndex={index} />
          )}

          {/* Strategy Notes */}
          {lead.strategy_notes && (
            <div className="mt-4 p-3 bg-slate-50 rounded-lg">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                Strategy Notes
              </h4>
              <p className="text-sm text-slate-600">{lead.strategy_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function FitScoreBadge({ score }) {
  let colorClass = "bg-red-50 text-red-700 border-red-200";
  if (score >= 8) colorClass = "bg-emerald-50 text-emerald-700 border-emerald-200";
  else if (score >= 5) colorClass = "bg-amber-50 text-amber-700 border-amber-200";

  return (
    <div
      className={`w-12 h-12 rounded-full border-2 flex items-center justify-center font-bold text-lg shrink-0 ${colorClass}`}
      data-testid="fit-score-badge"
    >
      {score}
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <div className="bg-slate-50 rounded-lg p-3">
      <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
      <p className="text-sm font-semibold text-slate-700 mt-0.5 capitalize">{value}</p>
    </div>
  );
}

export function MessageCard({ message, highlighted = false, testIdPrefix = "msg" }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.message);
      setCopied(true);
      toast.success("Message copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy");
    }
  };

  return (
    <div
      className={`rounded-lg border p-3 transition-colors ${
        highlighted
          ? "border-amber-200 bg-amber-50/50"
          : "border-slate-200 bg-white hover:bg-slate-50/50"
      }`}
      data-testid={`${testIdPrefix}-message-${message.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Badge
              variant="outline"
              className="text-[10px] font-medium uppercase tracking-wider px-1.5 py-0"
            >
              {message.type}
            </Badge>
            {highlighted && <Star className="h-3 w-3 text-amber-500 fill-amber-500" />}
          </div>
          <p className="text-sm text-slate-800 leading-relaxed">{message.message}</p>
          {message.rationale && (
            <p className="text-xs text-slate-400 mt-1.5 italic">{message.rationale}</p>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="shrink-0 h-8 w-8 p-0 rounded-full hover:bg-slate-200"
          data-testid={`${testIdPrefix}-copy-${message.id}`}
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-emerald-600" />
          ) : (
            <Copy className="h-3.5 w-3.5 text-slate-400" />
          )}
        </Button>
      </div>
    </div>
  );
}
