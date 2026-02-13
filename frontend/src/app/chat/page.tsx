/**
 * Chat Page — Enterprise AI chat with session management.
 * Clean layout: collapsible sidebar + full-height chat panel.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MessageSquare, Plus, Clock, ChevronLeft, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { v2Chat, type ChatSession } from '@/lib/api-v2';
import { ChatPanel } from '@/components/domain/chat/ChatPanel';

export default function ChatPage() {
  const [selectedSession, setSelectedSession] = useState<string | undefined>();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const { data: sessionsData } = useQuery({
    queryKey: ['v2', 'chat', 'sessions'],
    queryFn: () => v2Chat.sessions(),
    staleTime: 30_000,
    retry: 1,
  });

  const sessions = sessionsData?.sessions || [];

  return (
    <div className="h-[calc(100vh-4rem)] flex">
      {/* Sessions sidebar */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="hidden lg:flex flex-col border-r border-border bg-muted/50 overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                History
              </h3>
              <button
                onClick={() => setSelectedSession(undefined)}
                className="h-7 w-7 rounded-lg flex items-center justify-center bg-blue-500 hover:bg-blue-600 text-white transition-colors shadow-md shadow-blue-500/20"
                title="New chat"
              >
                <Plus className="h-3.5 w-3.5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
              {sessions.length === 0 && (
                <div className="flex flex-col items-center py-12 text-muted-foreground">
                  <MessageSquare className="h-8 w-8 opacity-30 mb-2" />
                  <p className="text-[10px] font-mono">No conversations yet</p>
                </div>
              )}

              {sessions.map((s: ChatSession) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedSession(s.id)}
                  className={`w-full text-left rounded-xl px-3 py-2.5 transition-all group ${
                    selectedSession === s.id
                      ? 'bg-accent/10 border border-accent/20 text-accent'
                      : 'hover:bg-muted text-muted-foreground border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-50" />
                    <span className="truncate text-xs font-medium">
                      {s.title || 'Untitled'}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 mt-1 ml-6 text-[10px] opacity-50 font-mono">
                    <Clock className="h-2.5 w-2.5" />
                    {new Date(s.updated_at).toLocaleDateString('vi-VN')}
                  </div>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toggle sidebar button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="hidden lg:flex h-full w-4 items-center justify-center border-r border-border hover:bg-muted transition-colors"
      >
        {sidebarOpen ? (
          <ChevronLeft className="h-3 w-3 text-slate-400" />
        ) : (
          <ChevronRight className="h-3 w-3 text-slate-400" />
        )}
      </button>

      {/* Main chat */}
      <div className="flex-1 min-w-0">
        <ChatPanel key={selectedSession || 'new'} />
      </div>
    </div>
  );
}
