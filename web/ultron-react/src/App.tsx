import { useState } from 'react';
import { AuthPage } from './components/AuthPage';
import { ResponsiveAIAssistant } from './components/ResponsiveAIAssistant';
import { Toaster } from './components/ui/sonner';
import { PyBridgeProvider } from './hooks/usePyBridge';

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
    <PyBridgeProvider>
      <div className="flex flex-col h-full w-full bg-gray-950 overflow-hidden">
        <div className="flex-1 relative overflow-hidden">
          {currentView === 'auth' && <AuthPage onLogin={handleLogin} />}
          {currentView === 'app' && <ResponsiveAIAssistant authenticatedUser={authenticatedUser} />}
        </div>
        <Toaster />
      </div>
    </PyBridgeProvider>
  );
}
