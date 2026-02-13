import { renderHook } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { usePagination } from '@/hooks/usePagination';
import type { ReactNode } from 'react';

const wrapper = ({ children }: { children: ReactNode }) => <MemoryRouter>{children}</MemoryRouter>;

describe('usePagination', () => {
  it('defaults to page 1', () => {
    const { result } = renderHook(() => usePagination(), { wrapper });
    expect(result.current.page).toBe(1);
  });

  it('uses defaultPageSize from options', () => {
    const { result } = renderHook(() => usePagination({ defaultPageSize: 10 }), { wrapper });
    expect(result.current.pageSize).toBe(10);
  });

  it('uses 20 as the default pageSize when no option is given', () => {
    const { result } = renderHook(() => usePagination(), { wrapper });
    expect(result.current.pageSize).toBe(20);
  });

  it('paginates items correctly for page 1', () => {
    const { result } = renderHook(() => usePagination({ defaultPageSize: 5 }), { wrapper });

    const items = Array.from({ length: 12 }, (_, i) => i + 1);
    const paginated = result.current.paginate(items);

    expect(paginated.items).toEqual([1, 2, 3, 4, 5]);
  });

  it('returns correct totalPages', () => {
    const { result } = renderHook(() => usePagination({ defaultPageSize: 5 }), { wrapper });

    const items = Array.from({ length: 12 }, (_, i) => i + 1);
    const paginated = result.current.paginate(items);

    // 12 items / 5 per page = 3 pages (ceil)
    expect(paginated.totalPages).toBe(3);
  });

  it('returns correct totalItems', () => {
    const { result } = renderHook(() => usePagination({ defaultPageSize: 5 }), { wrapper });

    const items = Array.from({ length: 12 }, (_, i) => i + 1);
    const paginated = result.current.paginate(items);

    expect(paginated.totalItems).toBe(12);
  });

  it('returns at least 1 totalPages even for empty arrays', () => {
    const { result } = renderHook(() => usePagination({ defaultPageSize: 5 }), { wrapper });

    const paginated = result.current.paginate([]);

    expect(paginated.totalPages).toBe(1);
    expect(paginated.totalItems).toBe(0);
    expect(paginated.items).toEqual([]);
  });
});
