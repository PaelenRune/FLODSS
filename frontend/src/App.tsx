import React from 'react';
import { AuthProvider } from './context/AuthContext';
import { Dashboard } from './pages/Dashboard';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  );
};

export default App;
