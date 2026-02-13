import { renderHook, act } from '@testing-library/react';
import { useSwipeGesture } from '@/hooks/useSwipeGesture';
import type { TouchEvent as ReactTouchEvent } from 'react';

/**
 * Creates a mock TouchEvent with the given coordinates.
 * Uses `unknown` intermediate cast to satisfy strict TypeScript.
 */
const createMockTouchEvent = (clientX: number, clientY: number): ReactTouchEvent => {
  return {
    touches: [{ clientX, clientY }],
    changedTouches: [{ clientX, clientY }],
    preventDefault: vi.fn(),
  } as unknown as ReactTouchEvent;
};

// ──────────────────────────────────────
// Initial state & structure
// ──────────────────────────────────────

describe('useSwipeGesture', () => {
  it('returns correct initial state', () => {
    const { result } = renderHook(() => useSwipeGesture());

    expect(result.current.state).toEqual({
      isSwiping: false,
      direction: null,
      deltaX: 0,
      deltaY: 0,
      velocity: 0,
    });
  });

  it('returns onTouchStart, onTouchMove, and onTouchEnd handlers', () => {
    const { result } = renderHook(() => useSwipeGesture());

    expect(typeof result.current.handlers.onTouchStart).toBe('function');
    expect(typeof result.current.handlers.onTouchMove).toBe('function');
    expect(typeof result.current.handlers.onTouchEnd).toBe('function');
  });

  it('provides a reset function', () => {
    const { result } = renderHook(() => useSwipeGesture());

    expect(typeof result.current.reset).toBe('function');
  });

  // ──────────────────────────────────────
  // Touch lifecycle
  // ──────────────────────────────────────

  it('sets isSwiping to true on touch start', () => {
    const { result } = renderHook(() => useSwipeGesture());

    act(() => {
      result.current.handlers.onTouchStart(createMockTouchEvent(100, 100));
    });

    expect(result.current.state.isSwiping).toBe(true);
  });

  it('resets state after touch end', () => {
    const { result } = renderHook(() => useSwipeGesture());

    act(() => {
      result.current.handlers.onTouchStart(createMockTouchEvent(200, 100));
    });

    act(() => {
      result.current.handlers.onTouchEnd(createMockTouchEvent(50, 100));
    });

    // handleTouchEnd calls reset() internally
    expect(result.current.state.isSwiping).toBe(false);
    expect(result.current.state.deltaX).toBe(0);
    expect(result.current.state.deltaY).toBe(0);
  });

  // ──────────────────────────────────────
  // Swipe direction callbacks
  // ──────────────────────────────────────

  it('calls onSwipeLeft when swiping left past threshold', () => {
    const onSwipeLeft = vi.fn();
    const { result } = renderHook(() => useSwipeGesture({ threshold: 50 }, { onSwipeLeft }));

    act(() => {
      result.current.handlers.onTouchStart(createMockTouchEvent(200, 100));
    });

    act(() => {
      result.current.handlers.onTouchEnd(createMockTouchEvent(100, 100));
    });

    expect(onSwipeLeft).toHaveBeenCalledTimes(1);
  });

  it('calls onSwipeRight when swiping right past threshold', () => {
    const onSwipeRight = vi.fn();
    const { result } = renderHook(() => useSwipeGesture({ threshold: 50 }, { onSwipeRight }));

    act(() => {
      result.current.handlers.onTouchStart(createMockTouchEvent(100, 100));
    });

    act(() => {
      result.current.handlers.onTouchEnd(createMockTouchEvent(250, 100));
    });

    expect(onSwipeRight).toHaveBeenCalledTimes(1);
  });

  it('calls onSwipeDown when swiping downward past threshold', () => {
    const onSwipeDown = vi.fn();
    const { result } = renderHook(() => useSwipeGesture({ threshold: 50 }, { onSwipeDown }));

    act(() => {
      result.current.handlers.onTouchStart(createMockTouchEvent(100, 100));
    });

    act(() => {
      result.current.handlers.onTouchEnd(createMockTouchEvent(100, 250));
    });

    expect(onSwipeDown).toHaveBeenCalledTimes(1);
  });

  it('calls onSwipeUp when swiping upward past threshold', () => {
    const onSwipeUp = vi.fn();
    const { result } = renderHook(() => useSwipeGesture({ threshold: 50 }, { onSwipeUp }));

    act(() => {
      result.current.handlers.onTouchStart(createMockTouchEvent(100, 200));
    });

    act(() => {
      result.current.handlers.onTouchEnd(createMockTouchEvent(100, 50));
    });

    expect(onSwipeUp).toHaveBeenCalledTimes(1);
  });

  // ──────────────────────────────────────
  // Threshold enforcement
  // ──────────────────────────────────────

  it('does not trigger swipe callback when below threshold and velocity', () => {
    vi.useFakeTimers();

    const onSwipeLeft = vi.fn();
    const onSwipeRight = vi.fn();
    const { result } = renderHook(() =>
      useSwipeGesture({ threshold: 100 }, { onSwipeLeft, onSwipeRight }),
    );

    act(() => {
      result.current.handlers.onTouchStart(createMockTouchEvent(100, 100));
    });

    // Advance clock so velocity is very low (distance / time → near zero)
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    act(() => {
      // 30px movement, well below the 100px threshold
      result.current.handlers.onTouchEnd(createMockTouchEvent(130, 100));
    });

    expect(onSwipeLeft).not.toHaveBeenCalled();
    expect(onSwipeRight).not.toHaveBeenCalled();

    vi.useRealTimers();
  });

  // ──────────────────────────────────────
  // onSwipeEnd callback
  // ──────────────────────────────────────

  it('calls onSwipeEnd with final state', () => {
    const onSwipeEnd = vi.fn();
    const { result } = renderHook(() => useSwipeGesture({ threshold: 50 }, { onSwipeEnd }));

    act(() => {
      result.current.handlers.onTouchStart(createMockTouchEvent(200, 100));
    });

    act(() => {
      result.current.handlers.onTouchEnd(createMockTouchEvent(50, 100));
    });

    expect(onSwipeEnd).toHaveBeenCalledTimes(1);

    const endState = onSwipeEnd.mock.calls[0][0] as {
      isSwiping: boolean;
      direction: string | null;
      deltaX: number;
      deltaY: number;
      velocity: number;
    };

    expect(endState.isSwiping).toBe(false);
    expect(endState.direction).toBe('left');
    expect(endState.deltaX).toBe(-150);
  });
});
