import React, { useState, useEffect, useRef } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card } from './ui/card';
import { Label } from './ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Sparkles, Mail, Lock, User, Minus, Square, X, Copy } from 'lucide-react';
import { toast } from 'sonner';
import { createInitials, normalizeEmail } from '../lib/app-utils';
import { usePyBridgeContext } from '../hooks/usePyBridge';

interface AuthPageProps {
  onLogin: (email: string, name: string) => void;
}

interface StoredUser {
  name: string;
  email: string;
  password: string;
  createdAt: string;
}

function getStoredUser(email: string): StoredUser | null {
  const key = `user_${email}`;
  const rawUser = localStorage.getItem(key);

  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as StoredUser;
  } catch (error) {
    console.warn(`Unable to read stored user "${key}".`, error);
    localStorage.removeItem(key);
    return null;
  }
}

export function AuthPage({ onLogin }: AuthPageProps) {
  const { isConnected } = usePyBridgeContext();
  const [isMaximized, setIsMaximized] = useState(false);
  const draggingRef = useRef(false);
  const startPosRef = useRef({ x: 0, y: 0 });

  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupConfirmPassword, setSignupConfirmPassword] = useState('');

  const handleMinimize = () => {
    window.pyBridge?.minimize_window?.();
  };

  const handleMaximize = () => {
    setIsMaximized(!isMaximized);
    window.pyBridge?.maximize_window?.();
  };

  const handleClose = () => {
    window.pyBridge?.close_window?.();
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!isConnected || !window.pyBridge?.move_window) return;
    
    draggingRef.current = true;
    startPosRef.current = { x: e.clientX, y: e.clientY };

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!draggingRef.current) return;
      
      const globalX = moveEvent.screenX - startPosRef.current.x;
      const globalY = moveEvent.screenY - startPosRef.current.y;
      
      (window as any).pyBridge?.move_window?.(globalX, globalY);
    };

    const handleMouseUp = () => {
      draggingRef.current = false;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  useEffect(() => {
    try {
      const savedProfile = localStorage.getItem('userProfile');
      if (savedProfile) {
        const parsed = JSON.parse(savedProfile);
        if (parsed.email) {
          setLoginEmail(parsed.email);
        }
      }
    } catch (error) {
      console.warn('Failed to load saved email', error);
    }
  }, []);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();

    const normalizedEmail = normalizeEmail(loginEmail);
    
    if (!normalizedEmail || !loginPassword) {
      toast.error('Please fill in all fields');
      return;
    }

    if (window.pyBridge) {
      const onLoginReady = (res: string) => {
        (window.pyBridge as any)?.loginReady?.disconnect?.(onLoginReady); // unsubscribe
        try {
          const data = JSON.parse(res);
          if (data.success) {
            toast.success('Welcome back!');
            localStorage.setItem(
              'userProfile',
              JSON.stringify({
                name: data.name || normalizedEmail,
                email: normalizedEmail,
                avatar: '',
                initials: createInitials(data.name || normalizedEmail),
              })
            );
            onLogin(normalizedEmail, data.name || normalizedEmail);
          } else {
            toast.error(data.message || 'Invalid credentials');
          }
        } catch {
          toast.error('Failed to process login response.');
        }
      };

      (window.pyBridge as any)?.loginReady?.connect?.(onLoginReady);
      (window.pyBridge as any).login?.(normalizedEmail, loginPassword);
      return;
    }

    // Mock authentication - in production, this would call an API
    const userData = getStoredUser(normalizedEmail);
    if (userData) {
      if (userData.password === loginPassword) {
        localStorage.setItem(
          'userProfile',
          JSON.stringify({
            name: userData.name,
            email: normalizedEmail,
            avatar: '',
            initials: createInitials(userData.name),
          })
        );
        toast.success('Welcome back!');
        onLogin(normalizedEmail, userData.name);
      } else {
        toast.error('Invalid password');
      }
    } else {
      toast.error('Account not found. Please sign up.');
    }
  };

  const handleSignup = (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedName = signupName.trim();
    const normalizedEmail = normalizeEmail(signupEmail);

    if (!trimmedName || !normalizedEmail || !signupPassword || !signupConfirmPassword) {
      toast.error('Please fill in all fields');
      return;
    }

    if (signupPassword !== signupConfirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    if (signupPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }

    if ((window as any).pyBridge) {
      const onSignupReady = (res: string) => {
        (window as any).pyBridge?.signupReady?.disconnect?.(onSignupReady); // unsubscribe
        try {
          const data = JSON.parse(res);
          if (data.success) {
            toast.success('Account created successfully!');
            localStorage.setItem(
              'userProfile',
              JSON.stringify({
                name: trimmedName,
                email: normalizedEmail,
                avatar: '',
                initials: createInitials(trimmedName),
              })
            );
            onLogin(normalizedEmail, trimmedName);
          } else {
            toast.error(data.message || 'Failed to create account');
          }
        } catch {
          toast.error('Failed to process signup response.');
        }
      };

      (window as any).pyBridge?.signupReady?.connect?.(onSignupReady);
      (window as any).pyBridge.signup?.(trimmedName, normalizedEmail, signupPassword);
      return;
    }

    // Check if user already exists
    const existingUser = getStoredUser(normalizedEmail);
    if (existingUser) {
      toast.error('Account already exists. Please login.');
      return;
    }

    // Create new user
    const userData: StoredUser = {
      name: trimmedName,
      email: normalizedEmail,
      password: signupPassword,
      createdAt: new Date().toISOString()
    };

    localStorage.setItem(`user_${normalizedEmail}`, JSON.stringify(userData));
    localStorage.setItem(
      'userProfile',
      JSON.stringify({
        name: trimmedName,
        email: normalizedEmail,
        avatar: '',
        initials: createInitials(trimmedName),
      })
    );
    toast.success('Account created successfully!');
    onLogin(normalizedEmail, trimmedName);
  };

  return (
    <div className="h-full bg-gradient-to-br from-blue-900 via-cyan-800 to-blue-800 relative overflow-hidden flex flex-col">
      {/* Integrated Title Bar */}
      <div className="flex items-center justify-between h-10 w-full bg-transparent text-gray-400 select-none z-50">
        <div className="flex-1 h-full flex items-center pl-4 font-semibold text-sm text-gray-200 cursor-move" onMouseDown={handleMouseDown}>
          U.L.T.R.O.N Assistant
        </div>
        <div className="flex h-full">
          <button onClick={handleMinimize} className="flex items-center justify-center w-12 h-full hover:bg-white/10 hover:text-white transition-colors">
            <Minus size={16} />
          </button>
          <button onClick={handleMaximize} className="flex items-center justify-center w-12 h-full hover:bg-white/10 hover:text-white transition-colors">
            {isMaximized ? <Copy size={14} /> : <Square size={14} />}
          </button>
          <button onClick={handleClose} className="flex items-center justify-center w-12 h-full hover:bg-red-600 hover:text-white transition-colors">
            <X size={16} />
          </button>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center relative">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-cyan-500/20 to-blue-700/20"></div>
        <div className="absolute top-20 left-10 w-64 h-64 bg-cyan-400/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-10 w-80 h-80 bg-blue-400/10 rounded-full blur-3xl"></div>

        {/* Auth Card */}
        <Card className="relative z-10 w-full max-w-md mx-4 p-8 backdrop-blur-lg bg-white/10 border-white/20">
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl text-white mb-2">Welcome to AI Assistant</h1>
            <p className="text-blue-200">Sign in to continue your journey</p>
          </div>

          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2 bg-gray-800/50 mb-6">
              <TabsTrigger value="login" className="text-white">Login</TabsTrigger>
              <TabsTrigger value="signup" className="text-white">Sign Up</TabsTrigger>
            </TabsList>

            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <Label htmlFor="login-email" className="text-white mb-2 block">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      id="login-email"
                      name="email"
                      type="email"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      placeholder="your@email.com"
                      className="bg-white/10 border-white/20 text-white placeholder:text-white/60 pl-10"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="login-password" className="text-white mb-2 block">Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      id="login-password"
                      name="password"
                      type="password"
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="••••••••"
                      className="bg-white/10 border-white/20 text-white placeholder:text-white/60 pl-10"
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full bg-cyan-600 hover:bg-cyan-500 text-white border-0"
                >
                  Sign In
                </Button>

                <div className="text-center">
                  <button
                    type="button"
                    className="text-cyan-400 hover:text-cyan-300 text-sm"
                    onClick={() => toast.info('Password reset coming soon!')}
                  >
                    Forgot password?
                  </button>
                </div>
              </form>
            </TabsContent>

            <TabsContent value="signup">
              <form onSubmit={handleSignup} className="space-y-4">
                <div>
                  <Label htmlFor="signup-name" className="text-white mb-2 block">Name</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      id="signup-name"
                      name="name"
                      type="text"
                      value={signupName}
                      onChange={(e) => setSignupName(e.target.value)}
                      placeholder="John Doe"
                      className="bg-white/10 border-white/20 text-white placeholder:text-white/60 pl-10"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="signup-email" className="text-white mb-2 block">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      id="signup-email"
                      name="email"
                      type="email"
                      value={signupEmail}
                      onChange={(e) => setSignupEmail(e.target.value)}
                      placeholder="your@email.com"
                      className="bg-white/10 border-white/20 text-white placeholder:text-white/60 pl-10"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="signup-password" className="text-white mb-2 block">Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      id="signup-password"
                      name="password"
                      type="password"
                      value={signupPassword}
                      onChange={(e) => setSignupPassword(e.target.value)}
                      placeholder="••••••••"
                      className="bg-white/10 border-white/20 text-white placeholder:text-white/60 pl-10"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="signup-confirm-password" className="text-white mb-2 block">Confirm Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      id="signup-confirm-password"
                      name="confirmPassword"
                      type="password"
                      value={signupConfirmPassword}
                      onChange={(e) => setSignupConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      className="bg-white/10 border-white/20 text-white placeholder:text-white/60 pl-10"
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full bg-cyan-600 hover:bg-cyan-500 text-white border-0"
                >
                  Create Account
                </Button>

                <p className="text-xs text-blue-200 text-center">
                  By signing up, you agree to our Terms of Service and Privacy Policy
                </p>
              </form>
            </TabsContent>
          </Tabs>

          <div className="mt-6 pt-6 border-t border-white/10">
            <p className="text-center text-blue-200 text-sm">
              Demo accounts are stored locally
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
