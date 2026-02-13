/**
 * VirtualList — High-performance virtualized list using @tanstack/react-virtual
 *
 * Renders only visible items + buffer, enabling smooth scrolling for 1000+ items.
 * Drop-in replacement for map()-based rendering patterns.
 */

import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { cn } from '@/lib/utils';

interface VirtualListProps<T> {
  items: T[];
  /** Estimated height of each item in pixels */
  estimateSize: number;
  /** Max visible height before scroll — defaults to 600px */
  maxHeight?: number;
  /** Extra items to render above/below viewport */
  overscan?: number;
  /** Render function for each item */
  renderItem: (item: T, index: number) => React.ReactNode;
  /** Unique key extractor */
  getKey: (item: T) => string | number;
  /** Container className */
  className?: string;
  /** Threshold below which the list renders normally (no virtualization) */
  virtualizeThreshold?: number;
}

export function VirtualList<T>({
  items,
  estimateSize,
  maxHeight = 600,
  overscan = 5,
  renderItem,
  getKey,
  className,
  virtualizeThreshold = 50,
}: VirtualListProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan,
  });

  // If below threshold, render normally for simpler animations
  if (items.length <= virtualizeThreshold) {
    return (
      <div className={cn('space-y-2', className)}>
        {items.map((item, i) => (
          <div key={getKey(item)}>{renderItem(item, i)}</div>
        ))}
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      className={cn('overflow-auto', className)}
      style={{ maxHeight, contain: 'strict' }}
    >
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {rowVirtualizer.getVirtualItems().map((virtualRow) => {
          const item = items[virtualRow.index];
          return (
            <div
              key={getKey(item)}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              {renderItem(item, virtualRow.index)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
