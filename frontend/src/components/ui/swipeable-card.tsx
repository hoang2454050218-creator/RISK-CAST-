/**
 * SwipeableCard - A card component with swipe-to-action functionality
 *
 * Features:
 * - Swipe left to reveal action buttons
 * - Swipe right for primary action
 * - Visual feedback during swipe
 * - Snap back animation
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface SwipeAction {
  id: string;
  label: string;
  icon?: ReactNode;
  color: string;
  bgColor: string;
  action: () => void;
}

interface SwipeableCardProps {
  children: ReactNode;
  leftActions?: SwipeAction[]; // Actions revealed on swipe right
  rightActions?: SwipeAction[]; // Actions revealed on swipe left
  onSwipeRight?: () => void; // Quick action on full swipe right
  onSwipeLeft?: () => void; // Quick action on full swipe left
  threshold?: number; // Swipe threshold in pixels
  className?: string;
  disabled?: boolean;
}

export function SwipeableCard({
  children,
  leftActions = [],
  rightActions = [],
  onSwipeRight,
  onSwipeLeft,
  threshold = 80,
  className,
  disabled = false,
}: SwipeableCardProps) {
  const [offsetX, setOffsetX] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const touchStart = useRef<{ x: number; y: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Max swipe distance based on actions
  const maxLeftOffset = leftActions.length > 0 ? Math.min(leftActions.length * 80, 160) : 0;
  const maxRightOffset = rightActions.length > 0 ? Math.min(rightActions.length * 80, 160) : 0;

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (disabled) return;
      const touch = e.touches[0];
      touchStart.current = { x: touch.clientX, y: touch.clientY };
      setIsTransitioning(false);
    },
    [disabled],
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (disabled || !touchStart.current) return;

      const touch = e.touches[0];
      const deltaX = touch.clientX - touchStart.current.x;
      const deltaY = touch.clientY - touchStart.current.y;

      // Only swipe horizontally if horizontal movement is dominant
      if (Math.abs(deltaX) > Math.abs(deltaY) * 1.5) {
        e.preventDefault();

        // Apply resistance at edges
        let newOffset = deltaX;
        if (deltaX > 0 && leftActions.length === 0) {
          newOffset = deltaX * 0.3; // Resistance when no left actions
        } else if (deltaX < 0 && rightActions.length === 0) {
          newOffset = deltaX * 0.3; // Resistance when no right actions
        } else if (deltaX > maxLeftOffset) {
          newOffset = maxLeftOffset + (deltaX - maxLeftOffset) * 0.3;
        } else if (deltaX < -maxRightOffset) {
          newOffset = -maxRightOffset + (deltaX + maxRightOffset) * 0.3;
        }

        setOffsetX(newOffset);
      }
    },
    [disabled, leftActions.length, rightActions.length, maxLeftOffset, maxRightOffset],
  );

  const handleTouchEnd = useCallback(() => {
    if (disabled || !touchStart.current) return;

    setIsTransitioning(true);

    // Full swipe triggers quick action
    if (offsetX > threshold * 1.5 && onSwipeRight) {
      onSwipeRight();
      setOffsetX(0);
    } else if (offsetX < -threshold * 1.5 && onSwipeLeft) {
      onSwipeLeft();
      setOffsetX(0);
    }
    // Partial swipe reveals actions
    else if (offsetX > threshold && leftActions.length > 0) {
      setOffsetX(maxLeftOffset);
    } else if (offsetX < -threshold && rightActions.length > 0) {
      setOffsetX(-maxRightOffset);
    }
    // Snap back
    else {
      setOffsetX(0);
    }

    touchStart.current = null;
  }, [
    disabled,
    offsetX,
    threshold,
    onSwipeRight,
    onSwipeLeft,
    leftActions.length,
    rightActions.length,
    maxLeftOffset,
    maxRightOffset,
  ]);

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node) &&
        offsetX !== 0
      ) {
        setIsTransitioning(true);
        setOffsetX(0);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [offsetX]);

  const handleActionClick = useCallback((action: SwipeAction) => {
    action.action();
    setIsTransitioning(true);
    setOffsetX(0);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;

    if (e.key === 'ArrowRight' && rightActions?.length) {
      e.preventDefault();
      // Trigger first right action (same as swipe left to reveal right actions)
      rightActions[0].action();
    } else if (e.key === 'ArrowLeft' && leftActions?.length) {
      e.preventDefault();
      // Trigger first left action
      leftActions[0].action();
    }
  };

  return (
    <div
      ref={containerRef}
      className={cn('relative overflow-hidden', className)}
      tabIndex={0}
      role="group"
      aria-label="Swipeable card. Use left and right arrow keys for actions."
      onKeyDown={handleKeyDown}
    >
      {/* Left actions (revealed on swipe right) */}
      {leftActions.length > 0 && (
        <div className="absolute inset-y-0 left-0 flex items-stretch">
          {leftActions.map((action) => (
            <button
              key={action.id}
              onClick={() => handleActionClick(action)}
              className={cn(
                'flex flex-col items-center justify-center px-4 min-w-[64px] transition-opacity',
                action.bgColor,
                offsetX > 20 ? 'opacity-100' : 'opacity-0',
              )}
              style={{ color: action.color }}
            >
              {action.icon}
              <span className="text-xs font-medium mt-1">{action.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Right actions (revealed on swipe left) */}
      {rightActions.length > 0 && (
        <div className="absolute inset-y-0 right-0 flex items-stretch">
          {rightActions.map((action) => (
            <button
              key={action.id}
              onClick={() => handleActionClick(action)}
              className={cn(
                'flex flex-col items-center justify-center px-4 min-w-[64px] transition-opacity',
                action.bgColor,
                offsetX < -20 ? 'opacity-100' : 'opacity-0',
              )}
              style={{ color: action.color }}
            >
              {action.icon}
              <span className="text-xs font-medium mt-1">{action.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Main content */}
      <div
        className={cn(
          'relative bg-card',
          isTransitioning && 'transition-transform duration-200 ease-out',
        )}
        style={{ transform: `translateX(${offsetX}px)` }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {children}
      </div>
    </div>
  );
}

export default SwipeableCard;
