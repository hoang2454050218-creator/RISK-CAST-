/**
 * I18n Provider - React Context for internationalization
 */

import { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { getTranslations } from './index';
import type { Locale, Translations, I18nContext } from './index';

const I18nContextImpl = createContext<I18nContext | null>(null);

interface I18nProviderProps {
  children: ReactNode;
  defaultLocale?: Locale;
}

export function I18nProvider({ children, defaultLocale = 'en' }: I18nProviderProps) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    // Try to get locale from localStorage
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('riskcast-locale');
      if (saved === 'en' || saved === 'vi') return saved;
    }
    return defaultLocale;
  });

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    localStorage.setItem('riskcast-locale', newLocale);
    document.documentElement.lang = newLocale;
  }, []);

  const t = getTranslations(locale);

  return (
    <I18nContextImpl.Provider value={{ locale, t, setLocale }}>{children}</I18nContextImpl.Provider>
  );
}

/**
 * Hook to access translations
 */
export function useI18n(): I18nContext {
  const context = useContext(I18nContextImpl);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

/**
 * Hook to get just the translations
 */
export function useTranslations(): Translations {
  return useI18n().t;
}

/**
 * Hook to get/set locale
 */
export function useLocale(): [Locale, (locale: Locale) => void] {
  const { locale, setLocale } = useI18n();
  return [locale, setLocale];
}

export default I18nProvider;
