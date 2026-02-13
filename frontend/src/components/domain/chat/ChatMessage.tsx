/**
 * ChatMessage — Enterprise-grade message bubble.
 * User: right-aligned blue gradient. Assistant: left-aligned with monospace data sections.
 */

import { motion } from 'framer-motion';
import { User, Sparkles } from 'lucide-react';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

export function ChatMessage({ role, content, isStreaming }: ChatMessageProps) {
  const isUser = role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex gap-2.5 mb-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      <div className={`shrink-0 h-7 w-7 rounded-lg flex items-center justify-center mt-0.5 ${
        isUser
          ? 'bg-gradient-to-br from-blue-500 to-blue-600 shadow-md shadow-blue-500/20'
          : 'bg-gradient-to-br from-muted to-muted/80'
      }`}>
        {isUser ? (
          <User className="h-3.5 w-3.5 text-white" />
        ) : (
          <Sparkles className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-[13px] leading-relaxed ${
          isUser
            ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-tr-md shadow-lg shadow-blue-500/15'
            : 'bg-muted text-foreground rounded-tl-md border border-border/50'
        }`}
      >
        <div className="whitespace-pre-wrap break-words">
          {content || (isStreaming && (
            <span className="flex items-center gap-1.5 text-slate-400">
              <span className="flex gap-0.5">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </span>
          ))}
          {content && isStreaming && (
            <span className="inline-block w-0.5 h-4 ml-0.5 bg-blue-400 animate-pulse rounded-full align-text-bottom" />
          )}
        </div>
      </div>
    </motion.div>
  );
}
