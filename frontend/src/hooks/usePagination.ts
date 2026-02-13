/**
 * usePagination — URL-synced pagination state.
 *
 * Stores page + pageSize in URL search params so that
 * filtered/paginated views are shareable and bookmarkable.
 */

import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router';

interface UsePaginationOptions {
  /** Default page size when none is in the URL. */
  defaultPageSize?: number;
}

interface PaginationState {
  /** Current page (1-indexed). */
  page: number;
  /** Items per page. */
  pageSize: number;
  /** Set the current page. */
  setPage: (page: number) => void;
  /** Set the page size (resets to page 1). */
  setPageSize: (size: number) => void;
  /** Calculate the slice for client-side pagination. */
  paginate: <T>(items: T[]) => { items: T[]; totalPages: number; totalItems: number };
}

export function usePagination({
  defaultPageSize = 20,
}: UsePaginationOptions = {}): PaginationState {
  const [searchParams, setSearchParams] = useSearchParams();

  const page = Number(searchParams.get('page')) || 1;
  const pageSize = Number(searchParams.get('pageSize')) || defaultPageSize;

  const setPage = useCallback(
    (newPage: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (newPage <= 1) {
          next.delete('page');
        } else {
          next.set('page', String(newPage));
        }
        return next;
      });
    },
    [setSearchParams],
  );

  const setPageSize = useCallback(
    (newSize: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set('pageSize', String(newSize));
        next.delete('page'); // reset to page 1
        return next;
      });
    },
    [setSearchParams],
  );

  const paginate = useCallback(
    <T>(items: T[]) => {
      const totalItems = items.length;
      const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
      const safePage = Math.min(page, totalPages);
      const start = (safePage - 1) * pageSize;
      const end = start + pageSize;
      return {
        items: items.slice(start, end),
        totalPages,
        totalItems,
      };
    },
    [page, pageSize],
  );

  return useMemo(
    () => ({ page, pageSize, setPage, setPageSize, paginate }),
    [page, pageSize, setPage, setPageSize, paginate],
  );
}
