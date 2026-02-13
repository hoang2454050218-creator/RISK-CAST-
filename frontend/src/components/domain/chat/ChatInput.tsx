/**
 * ChatInput — Enterprise-grade message input.
 * Auto-resize textarea, Enter to send, Shift+Enter newline.
 * Sleek dark mode design with gradient send button.
 */

import { useState, useRef, useCallback } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }, [value, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
  };

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div className="border-t border-border bg-background px-4 py-3">
      <div className="flex items-end gap-2 rounded-2xl border border-border bg-muted/50 pl-4 pr-2 py-2 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/10 transition-all">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder || 'Hỏi về đơn hàng, khách hàng, rủi ro...'}
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm text-foreground placeholder-muted-foreground focus:outline-none disabled:opacity-50 min-h-[24px] max-h-[140px] py-0.5"
        />
        <button
          onClick={handleSend}
          disabled={!canSend}
          className={`shrink-0 h-8 w-8 rounded-xl flex items-center justify-center transition-all ${
            canSend
              ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:scale-105 active:scale-95'
              : 'bg-muted text-muted-foreground cursor-not-allowed'
          }`}
          aria-label="Send"
        >
          {disabled ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Send className="h-3.5 w-3.5" />
          )}
        </button>
      </div>
      <p className="text-[9px] text-muted-foreground mt-1.5 text-center font-mono">
        Enter to send / Shift+Enter for new line
      </p>
    </div>
  );
}
