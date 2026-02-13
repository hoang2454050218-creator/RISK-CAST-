/**
 * useFormatters Hook
 *
 * Provides locale-aware formatters based on current i18n context.
 */

import { useMemo } from 'react';
import { useI18n } from './provider';
import { createLocaleFormatters } from '../formatters';

/**
 * Hook that returns locale-aware formatting functions
 *
 * @example
 * const { formatCurrency, formatDate } = useFormatters();
 * <span>{formatCurrency(1234.56)}</span>
 * <span>{formatDate(new Date())}</span>
 */
export function useFormatters() {
  const { locale } = useI18n();

  const formatters = useMemo(() => createLocaleFormatters(locale), [locale]);

  return formatters;
}

export default useFormatters;
