/**
 * ChatWidget — Floating chat bubble in bottom-right corner.
 *
 * Renders on every page. Click to expand into a chat panel.
 * Handles V2 auth automatically.
 */

import { useState } from 'react';
import { X, Loader2, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useV2Auth } from '@/hooks/useV2Auth';
import { ChatPanel } from './ChatPanel';

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const { isAuthenticated, isConnecting } = useV2Auth();
  const [unread, setUnread] = useState(0);

  const handleToggle = () => {
    setIsOpen(!isOpen);
    if (!isOpen) setUnread(0);
  };

  return (
    <>
      {/* Chat panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed bottom-20 right-4 z-50 w-[420px] h-[600px] max-h-[80vh] rounded-2xl shadow-2xl shadow-black/30 border border-border overflow-hidden"
            style={{ maxWidth: 'calc(100vw - 2rem)' }}
          >
            {/* Close button */}
            <button
              onClick={() => setIsOpen(false)}
              className="absolute top-3 right-3 z-10 h-7 w-7 rounded-lg flex items-center justify-center bg-muted hover:bg-muted/80 transition-colors"
            >
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>

            {isAuthenticated ? (
              <ChatPanel />
            ) : isConnecting ? (
              <div className="flex flex-col items-center justify-center h-full bg-background p-8">
                <Loader2 className="h-8 w-8 animate-spin text-accent mb-4" />
                <p className="text-sm text-muted-foreground">Connecting to RiskCast AI...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full bg-background p-8 text-center">
                <Sparkles className="h-8 w-8 text-accent/40 mb-4" />
                <p className="text-sm font-medium text-foreground mb-1">RiskCast AI Assistant</p>
                <p className="text-xs text-muted-foreground">Sign in to start chatting with the AI assistant.</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating button */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={handleToggle}
        className={`fixed bottom-4 right-4 z-50 h-14 w-14 rounded-2xl flex items-center justify-center shadow-xl transition-all ${
          isOpen
            ? 'bg-muted-foreground/80 shadow-muted-foreground/30'
            : 'bg-gradient-to-br from-accent to-accent-hover shadow-accent/30 hover:shadow-accent/50'
        }`}
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div key="close" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }}>
              <X className="h-5 w-5 text-accent-foreground" />
            </motion.div>
          ) : isConnecting ? (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <Loader2 className="h-5 w-5 text-accent-foreground animate-spin" />
            </motion.div>
          ) : (
            <motion.div key="chat" initial={{ rotate: 90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: -90, opacity: 0 }}>
              <Sparkles className="h-5 w-5 text-accent-foreground" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Unread badge */}
        {unread > 0 && !isOpen && (
          <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-destructive text-destructive-foreground text-[10px] font-bold flex items-center justify-center shadow-lg">
            {unread}
          </span>
        )}

        {/* Pulse ring */}
        {!isOpen && !isConnecting && (
          <span className="absolute inset-0 rounded-2xl animate-ping bg-accent opacity-20" />
        )}
      </motion.button>
    </>
  );
}
