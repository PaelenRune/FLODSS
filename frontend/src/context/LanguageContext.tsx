import React, { createContext, useContext, useState, useCallback } from 'react';

export type Language = 'tr' | 'en';

interface LanguageContextType {
  lang: Language;
  setLang: (lang: Language) => void;
  toggleLang: () => void;
  t: (tr: string, en: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<Language>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('flodss_lang');
      if (saved === 'tr' || saved === 'en') {
        return saved;
      }
    }
    return 'tr';
  });

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
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
