/**
 * useFilterState — Syncs filter state to URL params & localStorage saved views
 *
 * Provides:
 * - Bidirectional URL ↔ state sync (bookmarkable, shareable)
 * - Saved views persisted in localStorage (max 5 per page)
 * - Type-safe filter operations
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router';

// ─── Saved View ─────────────────────────────────────────────────
export interface SavedView<F extends Record<string, string>> {
  id: string;
  name: string;
  filters: F;
  isDefault?: boolean;
}

const MAX_SAVED_VIEWS = 5;

function getStorageKey(page: string) {
  return `riskcast:saved-views:${page}`;
}

function loadSavedViews<F extends Record<string, string>>(
  page: string,
  defaults: SavedView<F>[],
): SavedView<F>[] {
  try {
    const raw = localStorage.getItem(getStorageKey(page));
    if (raw) {
      const parsed = JSON.parse(raw) as SavedView<F>[];
      // Merge defaults (keep them, add user views)
      const defaultIds = new Set(defaults.map((d) => d.id));
      const userViews = parsed.filter((v) => !defaultIds.has(v.id));
      return [...defaults, ...userViews];
    }
  } catch { /* ignore */ }
  return defaults;
}

function persistSavedViews<F extends Record<string, string>>(
  page: string,
  views: SavedView<F>[],
) {
  try {
    localStorage.setItem(getStorageKey(page), JSON.stringify(views));
  } catch { /* ignore */ }
}

// ─── Hook ───────────────────────────────────────────────────────
export interface UseFilterStateOptions<F extends Record<string, string>> {
  /** Page identifier for localStorage key */
  page: string;
  /** Default filter values */
  defaults: F;
  /** Predefined saved views */
  defaultViews?: SavedView<F>[];
  /** Keys to sync with URL params */
  urlKeys?: (keyof F)[];
}

export function useFilterState<F extends Record<string, string>>({
  page,
  defaults,
  defaultViews = [],
  urlKeys,
}: UseFilterStateOptions<F>) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFiltersRaw] = useState<F>(() => {
    // Initialize from URL params
    const initial = { ...defaults };
    const keysToCheck = urlKeys ?? (Object.keys(defaults) as (keyof F)[]);
    for (const key of keysToCheck) {
      const param = searchParams.get(key as string);
      if (param) {
        (initial as Record<string, string>)[key as string] = param;
      }
    }
    return initial;
  });

  const [savedViews, setSavedViews] = useState<SavedView<F>[]>(() =>
    loadSavedViews(page, defaultViews),
  );
  const [activeViewId, setActiveViewId] = useState<string | null>(null);

  // ── Sync filters to URL ────────────────────────────────────
  const syncToUrl = useCallback(
    (newFilters: F) => {
      setSearchParams(
        (prev) => {
          const keysToSync = urlKeys ?? (Object.keys(defaults) as (keyof F)[]);
          for (const key of keysToSync) {
            const val = newFilters[key];
            const defaultVal = defaults[key];
            if (val && val !== defaultVal && val !== 'ALL') {
              prev.set(key as string, val);
            } else {
              prev.delete(key as string);
            }
          }
          return prev;
        },
        { replace: true },
      );
    },
    [setSearchParams, urlKeys, defaults],
  );

  // ── Set filters (updates state + URL) ──────────────────────
  const setFilters = useCallback(
    (update: Partial<F> | ((prev: F) => F)) => {
      setFiltersRaw((prev) => {
        const next = typeof update === 'function' ? update(prev) : { ...prev, ...update };
        syncToUrl(next);
        setActiveViewId(null);
        return next;
      });
    },
    [syncToUrl],
  );

  // ── Reset all filters ──────────────────────────────────────
  const resetFilters = useCallback(() => {
    setFiltersRaw(defaults);
    syncToUrl(defaults);
    setActiveViewId(null);
  }, [defaults, syncToUrl]);

  // ── Apply a saved view ─────────────────────────────────────
  const applyView = useCallback(
    (viewId: string) => {
      const view = savedViews.find((v) => v.id === viewId);
      if (!view) return;
      setFiltersRaw(view.filters);
      syncToUrl(view.filters);
      setActiveViewId(viewId);
    },
    [savedViews, syncToUrl],
  );

  // ── Save current filters as a view ─────────────────────────
  const saveCurrentView = useCallback(
    (name: string) => {
      const id = `user-${Date.now()}`;
      const newView: SavedView<F> = { id, name, filters: { ...filters } };
      const nonDefaults = savedViews.filter((v) => !v.isDefault);
      const all = [
        ...savedViews.filter((v) => v.isDefault),
        ...nonDefaults.slice(-(MAX_SAVED_VIEWS - 1)),
        newView,
      ];
      setSavedViews(all);
      persistSavedViews(page, all);
      setActiveViewId(id);
    },
    [filters, savedViews, page],
  );

  // ── Delete a saved view ────────────────────────────────────
  const deleteView = useCallback(
    (viewId: string) => {
      const updated = savedViews.filter((v) => v.id !== viewId || v.isDefault);
      setSavedViews(updated);
      persistSavedViews(page, updated);
      if (activeViewId === viewId) setActiveViewId(null);
    },
    [savedViews, page, activeViewId],
  );

  // ── Computed: has active filters ───────────────────────────
  const hasActiveFilters = useMemo(
    () => Object.keys(defaults).some((k) => filters[k as keyof F] !== defaults[k as keyof F]),
    [filters, defaults],
  );

  return {
    filters,
    setFilters,
    resetFilters,
    hasActiveFilters,
    savedViews,
    activeViewId,
    applyView,
    saveCurrentView,
    deleteView,
  };
}
