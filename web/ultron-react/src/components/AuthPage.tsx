import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card } from './ui/card';
import { Label } from './ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Sparkles, Mail, Lock, User } from 'lucide-react';
import { toast } from 'sonner';
import { createInitials, normalizeEmail } from '../lib/app-utils';

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
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupConfirmPassword, setSignupConfirmPassword] = useState('');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();

    const normalizedEmail = normalizeEmail(loginEmail);
    
    if (!normalizedEmail || !loginPassword) {
      toast.error('Please fill in all fields');
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
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-cyan-800 to-blue-800 relative overflow-hidden flex items-center justify-center">
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
                <Label className="text-white mb-2 block">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="bg-white/10 border-white/20 text-white placeholder:text-white/60 pl-10"
                  />
                </div>
              </div>

              <div>
                <Label className="text-white mb-2 block">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
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
                <Label className="text-white mb-2 block">Name</Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
                    type="text"
                    value={signupName}
                    onChange={(e) => setSignupName(e.target.value)}
                    placeholder="John Doe"
                    className="bg-white/10 border-white/20 text-white placeholder:text-white/60 pl-10"
                  />
                </div>
              </div>

              <div>
                <Label className="text-white mb-2 block">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
                    type="email"
                    value={signupEmail}
                    onChange={(e) => setSignupEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="bg-white/10 border-white/20 text-white placeholder:text-white/60 pl-10"
                  />
                </div>
              </div>

              <div>
                <Label className="text-white mb-2 block">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
                    type="password"
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value)}
                    placeholder="••••••••"
                    className="bg-white/10 border-white/20 text-white placeholder:text-white/60 pl-10"
                  />
                </div>
              </div>

              <div>
                <Label className="text-white mb-2 block">Confirm Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
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
  );
}
