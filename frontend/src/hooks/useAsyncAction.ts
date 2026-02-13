/**
 * useAsyncAction — Typed async action hook with loading, error, and success states.
 *
 * Provides a structured way to execute async operations (real or simulated)
 * with consistent loading indicators, error handling, and toast feedback.
 *
 * When the real API is connected, swap the `action` callback from
 * `simulateAsync(...)` to actual API calls — the rest of the UI stays the same.
 */

import { useState, useCallback, useRef } from 'react';

export interface AsyncActionState<T = void> {
  /** Whether the action is currently executing. */
  isLoading: boolean;
  /** The error from the last execution, if any. */
  error: Error | null;
  /** The result of the last successful execution. */
  data: T | null;
  /** Execute the action. Returns the result or throws. */
  execute: (...args: unknown[]) => Promise<T | undefined>;
  /** Reset the state (clear error/data). */
  reset: () => void;
}

interface UseAsyncActionOptions<T> {
  /** The async function to execute. */
  action: (...args: unknown[]) => Promise<T>;
  /** Called on success with the result. */
  onSuccess?: (data: T) => void;
  /** Called on error. */
  onError?: (error: Error) => void;
}

export function useAsyncAction<T = void>({
  action,
  onSuccess,
  onError,
}: UseAsyncActionOptions<T>): AsyncActionState<T> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [data, setData] = useState<T | null>(null);
  const mountedRef = useRef(true);

  const execute = useCallback(
    async (...args: unknown[]): Promise<T | undefined> => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await action(...args);
        if (mountedRef.current) {
          setData(result);
          setIsLoading(false);
          onSuccess?.(result);
        }
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        if (mountedRef.current) {
          setError(error);
          setIsLoading(false);
          onError?.(error);
        }
        return undefined;
      }
    },
    [action, onSuccess, onError],
  );

  const reset = useCallback(() => {
    setError(null);
    setData(null);
    setIsLoading(false);
  }, []);

  return { isLoading, error, data, execute, reset };
}

/**
 * Simulate an async operation with configurable delay.
 * Use this as a placeholder until the real API is wired.
 */
export function simulateAsync<T = void>(result?: T, delayMs = 1000): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(result as T), delayMs);
  });
}
