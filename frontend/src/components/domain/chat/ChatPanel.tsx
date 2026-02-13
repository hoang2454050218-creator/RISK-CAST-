/**
 * ChatPanel — Enterprise-grade AI chat interface.
 * Bloomberg terminal aesthetic: dark, dense, professional.
 * Features: streaming, suggestions, quick actions, typing indicator.
 */

import { useRef, useEffect, useState } from 'react';
import { RotateCcw, Sparkles, TrendingUp, Shield, AlertTriangle, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChat } from '@/hooks/useChat';
import { useSubmitFeedback } from '@/hooks/useFeedback';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { SuggestionCard } from './SuggestionCard';

const QUICK_PROMPTS = [
  { label: 'Tổng quan tuần', icon: TrendingUp, query: 'Tổng quan tuần này' },
  { label: 'Thanh toán quá hạn', icon: AlertTriangle, query: 'Tình hình thanh toán quá hạn' },
  { label: 'Đơn hàng rủi ro', icon: Shield, query: 'Đơn hàng nào cần chú ý?' },
  { label: 'Brief hôm nay', icon: Zap, query: 'Brief sáng nay' },
];

export function ChatPanel() {
  const { messages, isStreaming, suggestions, error, sendMessage, clearMessages, sessionId } = useChat();
  const feedbackMutation = useSubmitFeedback();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showWelcome, setShowWelcome] = useState(true);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, suggestions]);

  useEffect(() => {
    if (messages.length > 0) setShowWelcome(false);
  }, [messages.length]);

  const handleFeedback = (suggestionId: string, decision: 'accepted' | 'rejected', reasonCode?: string) => {
    feedbackMutation.mutate({ suggestionId, decision, reason_code: reasonCode });
  };

  const handleQuickPrompt = (query: string) => {
    setShowWelcome(false);
    sendMessage(query);
  };

  return (
    <div className="flex flex-col h-full bg-background overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-muted/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-success border-2 border-background" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-foreground tracking-tight">
              RiskCast AI
            </h2>
            <p className="text-[10px] text-muted-foreground font-mono">
              {isStreaming ? (
                <span className="text-blue-400 animate-pulse">Analyzing...</span>
              ) : sessionId ? (
                <span>Session active</span>
              ) : (
                <span>Ready</span>
              )}
            </p>
          </div>
        </div>
        <button
          onClick={() => { clearMessages(); setShowWelcome(true); }}
          className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
          title="New conversation"
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence mode="wait">
          {showWelcome && messages.length === 0 ? (
            <motion.div
              key="welcome"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex flex-col items-center justify-center h-full px-6 py-12"
            >
              {/* Logo */}
              <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-blue-500 via-blue-400 to-blue-600 flex items-center justify-center shadow-2xl shadow-blue-500/30 mb-6">
                <Sparkles className="h-8 w-8 text-white" />
              </div>

              <h3 className="text-lg font-bold text-foreground mb-1">
                RiskCast Intelligence
              </h3>
              <p className="text-sm text-muted-foreground text-center max-w-sm mb-8">
                Phân tích rủi ro thông minh dựa trên dữ liệu doanh nghiệp. Hỏi bằng tiếng Việt.
              </p>

              {/* Quick prompts grid */}
              <div className="grid grid-cols-2 gap-2 w-full max-w-md">
                {QUICK_PROMPTS.map((p) => {
                  const Icon = p.icon;
                  return (
                    <motion.button
                      key={p.query}
                      whileHover={{ scale: 1.02, y: -1 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => handleQuickPrompt(p.query)}
                      className="flex items-center gap-2.5 rounded-xl border border-border bg-card px-4 py-3 text-left hover:border-accent/50 hover:shadow-md hover:shadow-blue-500/5 transition-all group"
                    >
                      <div className="h-8 w-8 rounded-lg bg-muted flex items-center justify-center group-hover:bg-accent/10 transition-colors shrink-0">
                        <Icon className="h-4 w-4 text-muted-foreground group-hover:text-blue-500 transition-colors" />
                      </div>
                      <span className="text-xs font-medium text-foreground/80 group-hover:text-accent transition-colors">
                        {p.label}
                      </span>
                    </motion.button>
                  );
                })}
              </div>

              <p className="text-[10px] text-muted-foreground/50 mt-6 font-mono">
                Powered by Claude AI + Company Data
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="messages"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="px-4 py-4 space-y-1"
            >
              {messages.map((msg, i) => (
                <ChatMessage
                  key={i}
                  role={msg.role}
                  content={msg.content}
                  isStreaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'}
                />
              ))}

              {/* Error banner */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl bg-error/10 border border-error/20 px-4 py-3 text-sm text-error"
                >
                  {error}
                </motion.div>
              )}

              {/* Suggestions */}
              {suggestions.length > 0 && !isStreaming && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="space-y-2 pt-3"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-px flex-1 bg-gradient-to-r from-transparent via-accent/20 to-transparent" />
                    <span className="text-[10px] font-bold text-accent uppercase tracking-widest">
                      Recommended Actions
                    </span>
                    <div className="h-px flex-1 bg-gradient-to-r from-transparent via-accent/20 to-transparent" />
                  </div>
                  {suggestions.map((s) => (
                    <SuggestionCard
                      key={s.id}
                      suggestion={s}
                      onFeedback={(decision, reasonCode) => handleFeedback(s.id, decision, reasonCode)}
                    />
                  ))}
                </motion.div>
              )}

              <div ref={bottomRef} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input */}
      <ChatInput onSend={(q) => { setShowWelcome(false); sendMessage(q); }} disabled={isStreaming} />
    </div>
  );
}
