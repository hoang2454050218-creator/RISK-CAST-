import { renderHook, act } from '@testing-library/react';
import { useAsyncAction, simulateAsync } from '@/hooks/useAsyncAction';

// ── useAsyncAction ───────────────────────────────────────

describe('useAsyncAction', () => {
  it('has correct initial state', () => {
    const { result } = renderHook(() => useAsyncAction({ action: () => Promise.resolve() }));

    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.data).toBeNull();
  });

  it('sets isLoading to true during execution and false after', async () => {
    let resolveAction!: (value: string) => void;
    const action = () =>
      new Promise<string>((resolve) => {
        resolveAction = resolve;
      });

    const { result } = renderHook(() => useAsyncAction({ action }));

    // Start execution without resolving yet
    let executePromise: Promise<string | undefined>;
    act(() => {
      executePromise = result.current.execute();
    });

    expect(result.current.isLoading).toBe(true);

    // Resolve and flush
    await act(async () => {
      resolveAction('done');
      await executePromise;
    });

    expect(result.current.isLoading).toBe(false);
  });

  it('sets data on successful action', async () => {
    const { result } = renderHook(() =>
      useAsyncAction({ action: () => Promise.resolve('result-data') }),
    );

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toBe('result-data');
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it('calls onSuccess callback with the result', async () => {
    const onSuccess = vi.fn<(data: number) => void>();

    const { result } = renderHook(() =>
      useAsyncAction({ action: () => Promise.resolve(42), onSuccess }),
    );

    await act(async () => {
      await result.current.execute();
    });

    expect(onSuccess).toHaveBeenCalledWith(42);
  });

  it('sets error on failed action', async () => {
    const { result } = renderHook(() =>
      useAsyncAction({
        action: () => Promise.reject(new Error('test error')),
      }),
    );

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe('test error');
    expect(result.current.data).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it('calls onError callback with the error', async () => {
    const onError = vi.fn<(err: Error) => void>();

    const { result } = renderHook(() =>
      useAsyncAction({
        action: () => Promise.reject(new Error('boom')),
        onError,
      }),
    );

    await act(async () => {
      await result.current.execute();
    });

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ message: 'boom' }));
  });

  it('resets data and error when reset is called', async () => {
    const { result } = renderHook(() => useAsyncAction({ action: () => Promise.resolve('data') }));

    await act(async () => {
      await result.current.execute();
    });
    expect(result.current.data).toBe('data');

    act(() => {
      result.current.reset();
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });
});

// ── simulateAsync ────────────────────────────────────────

describe('simulateAsync', () => {
  it('resolves with the provided result after delay', async () => {
    const result = await simulateAsync('hello', 0);
    expect(result).toBe('hello');
  });

  it('resolves to undefined when no result is provided', async () => {
    const result = await simulateAsync(undefined, 0);
    expect(result).toBeUndefined();
  });
});
