/**
 * useSwipeGesture - Hook for handling swipe gestures on touch devices
 *
 * Features:
 * - Horizontal swipe detection (left/right)
 * - Vertical swipe detection (up/down)
 * - Configurable threshold
 * - Touch velocity tracking for faster swipes
 */

import { useState, useRef, useCallback } from 'react';
import type { TouchEvent } from 'react';

export type SwipeDirection = 'left' | 'right' | 'up' | 'down' | null;

interface SwipeState {
  isSwiping: boolean;
  direction: SwipeDirection;
  deltaX: number;
  deltaY: number;
  velocity: number;
}

interface SwipeConfig {
  threshold?: number; // Min distance to trigger swipe (default: 50px)
  velocityThreshold?: number; // Min velocity to trigger quick swipe (default: 0.3)
  preventScrollOnSwipe?: boolean;
}

interface SwipeHandlers {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  onSwipeMove?: (state: SwipeState) => void;
  onSwipeEnd?: (state: SwipeState) => void;
}

interface UseSwipeGestureReturn {
  handlers: {
    onTouchStart: (e: TouchEvent) => void;
    onTouchMove: (e: TouchEvent) => void;
    onTouchEnd: (e: TouchEvent) => void;
  };
  state: SwipeState;
  reset: () => void;
}

export function useSwipeGesture(
  config: SwipeConfig = {},
  handlers: SwipeHandlers = {},
): UseSwipeGestureReturn {
  const { threshold = 50, velocityThreshold = 0.3, preventScrollOnSwipe = false } = config;

  const { onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown, onSwipeMove, onSwipeEnd } = handlers;

  const [state, setState] = useState<SwipeState>({
    isSwiping: false,
    direction: null,
    deltaX: 0,
    deltaY: 0,
    velocity: 0,
  });

  const touchStart = useRef<{ x: number; y: number; time: number } | null>(null);

  const reset = useCallback(() => {
    setState({
      isSwiping: false,
      direction: null,
      deltaX: 0,
      deltaY: 0,
      velocity: 0,
    });
    touchStart.current = null;
  }, []);

  const handleTouchStart = useCallback((e: TouchEvent) => {
    const touch = e.touches[0];
    touchStart.current = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now(),
    };

    setState((prev) => ({
      ...prev,
      isSwiping: true,
      direction: null,
      deltaX: 0,
      deltaY: 0,
    }));
  }, []);

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      if (!touchStart.current) return;

      const touch = e.touches[0];
      const deltaX = touch.clientX - touchStart.current.x;
      const deltaY = touch.clientY - touchStart.current.y;
      const elapsed = Date.now() - touchStart.current.time;
      const velocity = Math.sqrt(deltaX * deltaX + deltaY * deltaY) / elapsed;

      // Determine direction based on larger delta
      let direction: SwipeDirection = null;
      if (Math.abs(deltaX) > Math.abs(deltaY)) {
        direction = deltaX > 0 ? 'right' : 'left';
      } else {
        direction = deltaY > 0 ? 'down' : 'up';
      }

      const newState: SwipeState = {
        isSwiping: true,
        direction,
        deltaX,
        deltaY,
        velocity,
      };

      setState(newState);
      onSwipeMove?.(newState);

      // Prevent scroll when swiping horizontally
      if (preventScrollOnSwipe && Math.abs(deltaX) > Math.abs(deltaY)) {
        e.preventDefault();
      }
    },
    [onSwipeMove, preventScrollOnSwipe],
  );

  const handleTouchEnd = useCallback(
    (e: TouchEvent) => {
      if (!touchStart.current) return;

      const changedTouch = e.changedTouches[0];
      const deltaX = changedTouch.clientX - touchStart.current.x;
      const deltaY = changedTouch.clientY - touchStart.current.y;
      const elapsed = Date.now() - touchStart.current.time;
      const velocity = Math.sqrt(deltaX * deltaX + deltaY * deltaY) / elapsed;

      const isQuickSwipe = velocity >= velocityThreshold;
      const absX = Math.abs(deltaX);
      const absY = Math.abs(deltaY);

      // Determine swipe direction and trigger handlers
      if (absX > absY) {
        // Horizontal swipe
        if (absX >= threshold || isQuickSwipe) {
          if (deltaX > 0) {
            onSwipeRight?.();
          } else {
            onSwipeLeft?.();
          }
        }
      } else {
        // Vertical swipe
        if (absY >= threshold || isQuickSwipe) {
          if (deltaY > 0) {
            onSwipeDown?.();
          } else {
            onSwipeUp?.();
          }
        }
      }

      const finalState: SwipeState = {
        isSwiping: false,
        direction: absX > absY ? (deltaX > 0 ? 'right' : 'left') : deltaY > 0 ? 'down' : 'up',
        deltaX,
        deltaY,
        velocity,
      };

      onSwipeEnd?.(finalState);
      reset();
    },
    [
      threshold,
      velocityThreshold,
      onSwipeLeft,
      onSwipeRight,
      onSwipeUp,
      onSwipeDown,
      onSwipeEnd,
      reset,
    ],
  );

  return {
    handlers: {
      onTouchStart: handleTouchStart,
      onTouchMove: handleTouchMove,
      onTouchEnd: handleTouchEnd,
    },
    state,
    reset,
  };
}

/**
 * SwipeAction - Component wrapper that adds swipe actions to children
 */
export interface SwipeAction {
  id: string;
  label: string;
  icon?: import('react').ReactNode;
  color: string;
  bgColor: string;
  action: () => void;
}

export default useSwipeGesture;
