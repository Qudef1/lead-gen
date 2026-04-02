import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { toast } from "sonner";
import { Send, Bot, User, Loader2, Info } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";

export function LeadChatPanel({ lead, isOpen, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg = { role: "user", content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: lead.conversation_id,
          lead_name: lead.name,
          messages: updatedMessages,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    } catch (e) {
      toast.error(`Chat error: ${e.message}`);
      // Remove the optimistically added user message on failure
      setMessages((prev) => prev.slice(0, -1));
      setInput(text);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent
        side="right"
        className="w-full sm:w-[480px] md:w-[520px] flex flex-col p-0 gap-0"
        data-testid="lead-chat-panel"
      >
        {/* Header */}
        <SheetHeader className="px-5 pt-5 pb-4 border-b border-slate-100 shrink-0">
          <SheetTitle className="flex items-center gap-2 text-[#1a2744]">
            <Bot className="h-5 w-5 text-[#10b981]" />
            <span>Ask AI about {lead.name}</span>
          </SheetTitle>
          {lead.company && (
            <p className="text-sm text-slate-500 mt-0.5">{lead.company}</p>
          )}
        </SheetHeader>

        {/* Context banner */}
        <div className="mx-4 mt-3 mb-1 flex items-start gap-2 rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-2.5 shrink-0">
          <Info className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
          <p className="text-xs text-emerald-700 leading-relaxed">
            GPT-5.1 has full access to this lead's research, analysis, pain points, and company data.
            Ask anything — strategy, objections, message ideas, or background info.
          </p>
        </div>

        {/* Messages */}
        <div
          className="flex-1 overflow-y-auto px-4 py-3 space-y-3"
          data-testid="chat-messages"
        >
          {messages.length === 0 && !isLoading && (
            <div className="text-center py-10 text-slate-400 text-sm">
              <Bot className="h-8 w-8 mx-auto mb-3 opacity-40" />
              <p>No messages yet. Ask something about this lead.</p>
              <p className="mt-2 text-xs text-slate-300">e.g. "What's the best angle to approach them?"</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <ChatBubble key={i} message={msg} />
          ))}

          {isLoading && (
            <div className="flex items-start gap-2" data-testid="chat-loading">
              <div className="w-7 h-7 rounded-full bg-[#10b981]/10 border border-[#10b981]/20 flex items-center justify-center shrink-0">
                <Bot className="h-3.5 w-3.5 text-[#10b981]" />
              </div>
              <div className="bg-slate-100 rounded-2xl rounded-tl-sm px-3.5 py-2.5">
                <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="px-4 pb-4 pt-2 border-t border-slate-100 shrink-0">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about this lead…"
              rows={2}
              className="flex-1 resize-none rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#10b981]/40 focus:border-[#10b981] transition-colors"
              disabled={isLoading}
              data-testid="chat-input"
            />
            <Button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              size="icon"
              className="h-10 w-10 shrink-0 rounded-xl bg-[#10b981] hover:bg-[#0d9469] text-white disabled:opacity-40"
              data-testid="chat-send-button"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="text-[10px] text-slate-400 mt-1.5 pl-1">
            Press Enter to send · Shift+Enter for new line
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function ChatBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex items-start gap-2 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
          isUser
            ? "bg-[#1a2744] text-white"
            : "bg-[#10b981]/10 border border-[#10b981]/20"
        }`}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5" />
        ) : (
          <Bot className="h-3.5 w-3.5 text-[#10b981]" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-[#1a2744] text-white rounded-tr-sm"
            : "bg-slate-100 text-slate-800 rounded-tl-sm"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
