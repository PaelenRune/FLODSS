import React from 'react';
import { LanguageProvider } from './context/LanguageContext';
import { AuthProvider } from './context/AuthContext';
import { Dashboard } from './pages/Dashboard';

export const App: React.FC = () => {
  return (
    <LanguageProvider>
      <AuthProvider>
        <Dashboard />
      </AuthProvider>
    </LanguageProvider>
  );
};

export default App;
