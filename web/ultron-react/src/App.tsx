import { useState } from 'react';
import { LandingPage } from './components/LandingPage';
import { AuthPage } from './components/AuthPage';
import { ResponsiveAIAssistant } from './components/ResponsiveAIAssistant';
import { Toaster } from './components/ui/sonner';

type AppView = 'landing' | 'auth' | 'app';

export default function App() {
  const [currentView, setCurrentView] = useState<AppView>('landing');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const [userName, setUserName] = useState('');

  const handleGetStarted = () => {
    setCurrentView('auth');
  };

  const handleLogin = (email: string, name: string) => {
    setUserEmail(email);
    setUserName(name);
    setIsAuthenticated(true);
    setCurrentView('app');
  };

  const handleBackToLanding = () => {
    setCurrentView('landing');
  };

  const handleShowAuth = () => {
    setCurrentView('auth');
  };

  if (currentView === 'landing') {
    return (
      <>
        <LandingPage onGetStarted={handleGetStarted} onLogin={handleShowAuth} />
        <Toaster />
      </>
    );
  }

  if (currentView === 'auth') {
    return (
      <>
        <AuthPage onLogin={handleLogin} onBack={handleBackToLanding} />
        <Toaster />
      </>
    );
  }

  return (
    <>
      <ResponsiveAIAssistant />
      <Toaster />
    </>
  );
}
