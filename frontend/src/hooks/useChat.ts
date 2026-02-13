/**
 * useChat — SSE streaming chat hook.
 *
 * Handles:
 * - Sending messages via POST (SSE response)
 * - Parsing chunk/done/error events
 * - Accumulating assistant response
 * - Extracting suggestions from done event
 */

import { useState, useCallback } from 'react';
import { v2Chat, type Suggestion } from '@/lib/api-v2';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export function useChat(initialSessionId?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(initialSessionId);

  const sendMessage = useCallback(
    async (content: string) => {
      setMessages((prev) => [...prev, { role: 'user', content }]);
      setIsStreaming(true);
      setSuggestions([]);
      setError(null);

      let assistantContent = '';

      try {
        const resp = await v2Chat.sendMessage(content, sessionId);
        const reader = resp.body!.getReader();
        const decoder = new TextDecoder();

        // Add empty assistant message
        setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;

            try {
              const data = JSON.parse(line.slice(6));

              switch (data.type) {
                case 'chunk':
                  assistantContent += data.content;
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      role: 'assistant',
                      content: assistantContent,
                    };
                    return updated;
                  });
                  break;

                case 'done':
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      role: 'assistant',
                      content: data.clean_content || assistantContent,
                    };
                    return updated;
                  });
                  if (data.suggestions?.length) setSuggestions(data.suggestions);
                  if (data.session_id) setSessionId(data.session_id);
                  break;

                case 'error':
                  setError(data.message);
                  if (!assistantContent) {
                    setMessages((prev) => prev.slice(0, -1));
                  }
                  break;
              }
            } catch {
              // Skip malformed lines
            }
          }
        }
      } catch {
        setError('Không thể kết nối server. Vui lòng thử lại.');
        if (!assistantContent) {
          setMessages((prev) => prev.slice(0, -1));
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [sessionId]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setSuggestions([]);
    setError(null);
    setSessionId(undefined);
  }, []);

  return { messages, isStreaming, suggestions, error, sessionId, sendMessage, clearMessages };
}
