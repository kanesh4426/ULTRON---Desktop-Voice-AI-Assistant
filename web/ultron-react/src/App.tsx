import { useState } from 'react';
import { AuthPage } from './components/AuthPage';
import { ResponsiveAIAssistant } from './components/ResponsiveAIAssistant';
import { Toaster } from './components/ui/sonner';

type AppView = 'auth' | 'app';
type AuthenticatedUser = {
  email: string;
  name: string;
};

export default function App() {
  const [currentView, setCurrentView] = useState<AppView>('auth');
  const [authenticatedUser, setAuthenticatedUser] = useState<AuthenticatedUser | null>(null);

  const handleLogin = (email: string, name: string) => {
    setAuthenticatedUser({ email, name });
    setCurrentView('app');
  };

  return (
    <>
      {currentView === 'auth' && <AuthPage onLogin={handleLogin} />}
      {currentView === 'app' && <ResponsiveAIAssistant authenticatedUser={authenticatedUser} />}
      <Toaster />
    </>
  );
}
