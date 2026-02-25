import { useState } from "react";
import { MessageCard } from "@/components/LeadCard";
import { ChevronDown, ChevronRight } from "lucide-react";

const TYPE_LABELS = {
  synergy: "Synergy",
  "question-based": "Question-Based",
  question: "Question-Based",
  "insight-based": "Insight-Based",
  insight: "Insight-Based",
  soft: "Soft Touch",
  "soft_touch": "Soft Touch",
  "soft touch": "Soft Touch",
  direct: "Direct Value Prop",
  "direct_value_prop": "Direct Value Prop",
  "direct value prop": "Direct Value Prop",
};

function normalizeType(type) {
  return TYPE_LABELS[type?.toLowerCase()] || type || "Other";
}

export function MessageGroup({ messages, leadIndex }) {
  const [expandedTypes, setExpandedTypes] = useState({});

  // Group messages by type
  const groups = {};
  for (const msg of messages) {
    const label = normalizeType(msg.type);
    if (!groups[label]) groups[label] = [];
    groups[label].push(msg);
  }

  const toggleType = (type) => {
    setExpandedTypes((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  return (
    <div data-testid={`lead-${leadIndex}-messages`}>
      <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
        All Message Variants
      </h4>
      <div className="space-y-2">
        {Object.entries(groups).map(([type, msgs]) => (
          <div
            key={type}
            className="border border-slate-200 rounded-lg overflow-hidden"
            data-testid={`lead-${leadIndex}-group-${type.toLowerCase().replace(/\s+/g, "-")}`}
          >
            <button
              onClick={() => toggleType(type)}
              className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
              data-testid={`lead-${leadIndex}-group-toggle-${type.toLowerCase().replace(/\s+/g, "-")}`}
            >
              <span className="text-sm font-medium text-[#1a2744]">
                {type}{" "}
                <span className="text-slate-400 font-normal">({msgs.length})</span>
              </span>
              {expandedTypes[type] ? (
                <ChevronDown className="h-4 w-4 text-slate-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-slate-400" />
              )}
            </button>
            {expandedTypes[type] && (
              <div className="p-3 space-y-2">
                {msgs.map((msg) => (
                  <MessageCard
                    key={msg.id}
                    message={msg}
                    testIdPrefix={`lead-${leadIndex}`}
                  />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
