/**
 * Pagination — Enterprise-grade pagination controls.
 *
 * Features:
 * - "Showing X–Y of Z items" summary
 * - First / Prev / [page buttons with ellipsis] / Next / Last
 * - Page size selector (10 / 20 / 50)
 * - Keyboard: Left/Right arrows to change pages
 * - Subtle, enterprise — not consumer-flashy
 */

import { useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface PaginationProps {
  /** Current page (1-indexed). */
  currentPage: number;
  /** Total number of pages. */
  totalPages: number;
  /** Called when user changes page. */
  onPageChange: (page: number) => void;
  /** Current page size. */
  pageSize: number;
  /** Called when user changes page size. */
  onPageSizeChange?: (size: number) => void;
  /** Total number of items across all pages. */
  totalItems: number;
  /** Available page size options. Default: [10, 20, 50]. */
  pageSizeOptions?: number[];
  /** Additional class names. */
  className?: string;
}

const MAX_VISIBLE_PAGES = 5;

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  pageSize,
  onPageSizeChange,
  totalItems,
  pageSizeOptions = [10, 20, 50],
  className,
}: PaginationProps) {
  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable)
        return;
      if (document.querySelector('[role="dialog"], [role="alertdialog"]')) return;

      if (e.key === 'ArrowLeft' && currentPage > 1) {
        e.preventDefault();
        onPageChange(currentPage - 1);
      }
      if (e.key === 'ArrowRight' && currentPage < totalPages) {
        e.preventDefault();
        onPageChange(currentPage + 1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentPage, totalPages, onPageChange]);

  // Calculate visible page range
  const getPageNumbers = useCallback((): (number | 'ellipsis')[] => {
    if (totalPages <= MAX_VISIBLE_PAGES) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    const pages: (number | 'ellipsis')[] = [];
    const half = Math.floor(MAX_VISIBLE_PAGES / 2);
    let start = Math.max(1, currentPage - half);
    let end = Math.min(totalPages, start + MAX_VISIBLE_PAGES - 1);

    if (end - start < MAX_VISIBLE_PAGES - 1) {
      start = Math.max(1, end - MAX_VISIBLE_PAGES + 1);
    }

    if (start > 1) {
      pages.push(1);
      if (start > 2) pages.push('ellipsis');
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    if (end < totalPages) {
      if (end < totalPages - 1) pages.push('ellipsis');
      pages.push(totalPages);
    }

    return pages;
  }, [currentPage, totalPages]);

  if (totalPages <= 1 && totalItems <= pageSize) return null;

  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  return (
    <div
      className={cn('flex flex-col sm:flex-row items-center justify-between gap-3 pt-4', className)}
    >
      {/* Summary + page size */}
      <div className="flex items-center gap-3 text-xs font-mono text-muted-foreground">
        <span>
          Showing{' '}
          <span className="text-foreground font-medium">
            {startItem}–{endItem}
          </span>{' '}
          of <span className="text-foreground font-medium">{totalItems}</span>
        </span>

        {onPageSizeChange && (
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="h-7 rounded border border-border bg-muted/50 px-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-accent/50"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size} / page
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Page buttons */}
      <div className="flex items-center gap-1">
        {/* First */}
        <PageButton
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          aria-label="First page"
        >
          <ChevronsLeft className="h-3.5 w-3.5" />
        </PageButton>

        {/* Prev */}
        <PageButton
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </PageButton>

        {/* Pages */}
        {getPageNumbers().map((page, idx) =>
          page === 'ellipsis' ? (
            <span
              key={`ellipsis-${idx}`}
              className="px-1 text-xs text-muted-foreground select-none"
            >
              ...
            </span>
          ) : (
            <PageButton
              key={page}
              onClick={() => onPageChange(page)}
              active={page === currentPage}
              aria-label={`Page ${page}`}
              aria-current={page === currentPage ? 'page' : undefined}
            >
              {page}
            </PageButton>
          ),
        )}

        {/* Next */}
        <PageButton
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          aria-label="Next page"
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </PageButton>

        {/* Last */}
        <PageButton
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          aria-label="Last page"
        >
          <ChevronsRight className="h-3.5 w-3.5" />
        </PageButton>
      </div>
    </div>
  );
}

function PageButton({
  children,
  active,
  disabled,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      {...props}
      disabled={disabled}
      className={cn(
        'inline-flex items-center justify-center h-7 min-w-7 rounded text-xs font-mono transition-colors',
        active
          ? 'bg-accent text-white font-semibold'
          : 'text-muted-foreground hover:text-foreground hover:bg-muted',
        disabled && 'opacity-30 pointer-events-none',
      )}
    >
      {children}
    </button>
  );
}
