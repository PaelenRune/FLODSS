import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export type Language = 'tr' | 'en';

interface LanguageContextType {
  lang: Language;
  setLang: (lang: Language) => void;
  toggleLang: () => void;
  t: (tr: string, en: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

const DEFAULT_LANGUAGE_CONTEXT: LanguageContextType = {
  lang: 'tr',
  setLang: () => {},
  toggleLang: () => {},
  t: (tr: string) => tr,
};

export const LanguageProvider: React.FC<{ children: React.ReactNode; initialLang?: Language }> = ({
  children,
  initialLang,
}) => {
  const [lang, setLangState] = useState<Language>(() => {
    if (initialLang === 'tr' || initialLang === 'en') {
      return initialLang;
    }
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('flodss_lang');
      if (saved === 'tr' || saved === 'en') {
        return saved;
      }
    }
    return 'tr';
  });

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = lang;
      document.title =
        lang === 'tr'
          ? 'Tesis Yerleşimi Optimizasyon ve Karar Destek Sistemi (FLODSS)'
          : 'Facility Layout Optimization & Decision Support System (FLODSS)';
    }
  }, [lang]);

  const setLang = useCallback((newLang: Language) => {
    setLangState(newLang);
    if (typeof window !== 'undefined') {
      localStorage.setItem('flodss_lang', newLang);
    }
  }, []);

  const toggleLang = useCallback(() => {
    setLangState((prev) => {
      const next = prev === 'tr' ? 'en' : 'tr';
      if (typeof window !== 'undefined') {
        localStorage.setItem('flodss_lang', next);
      }
      return next;
    });
  }, []);

  const t = useCallback(
    (tr: string, en: string) => {
      return lang === 'tr' ? tr : en;
    },
    [lang]
  );

  return (
    <LanguageContext.Provider value={{ lang, setLang, toggleLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  return context ?? DEFAULT_LANGUAGE_CONTEXT;
};
