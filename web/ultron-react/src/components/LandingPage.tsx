import React from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Mic, MessageSquare, Zap, Shield, Globe, Sparkles, ArrowRight, Check } from 'lucide-react';

interface LandingPageProps {
  onGetStarted: () => void;
  onLogin: () => void;
}

export function LandingPage({ onGetStarted, onLogin }: LandingPageProps) {
  const features = [
    {
      icon: <MessageSquare className="w-6 h-6" />,
      title: 'Smart Conversations',
      description: 'Engage in natural, intelligent conversations with our advanced AI assistant'
    },
    {
      icon: <Mic className="w-6 h-6" />,
      title: 'Voice Enabled',
      description: 'Speak naturally with voice input and get spoken responses'
    },
    {
      icon: <Zap className="w-6 h-6" />,
      title: 'Quick Actions',
      description: 'Access dozens of pre-built prompts for instant productivity'
    },
    {
      icon: <Globe className="w-6 h-6" />,
      title: 'Multi-Language',
      description: 'Communicate in multiple languages with real-time translation'
    },
    {
      icon: <Shield className="w-6 h-6" />,
      title: 'Privacy First',
      description: 'Your conversations are stored locally and never shared'
    },
    {
      icon: <Sparkles className="w-6 h-6" />,
      title: 'Beautiful UI',
      description: 'Stunning holographic interface with multiple themes'
    }
  ];

  const plans = [
    {
      name: 'Free',
      price: '$0',
      period: 'forever',
      features: [
        'Unlimited conversations',
        'Voice input & output',
        'Chat history',
        'Basic quick actions',
        'Mobile responsive'
      ],
      cta: 'Get Started',
      popular: false
    },
    {
      name: 'Pro',
      price: '$9.99',
      period: 'per month',
      features: [
        'Everything in Free',
        'Advanced AI models',
        'Custom quick actions',
        'Priority support',
        'Cloud sync',
        'Team collaboration'
      ],
      cta: 'Start Free Trial',
      popular: true
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: 'contact us',
      features: [
        'Everything in Pro',
        'Custom integrations',
        'Dedicated support',
        'SLA guarantees',
        'Advanced security',
        'Custom deployment'
      ],
      cta: 'Contact Sales',
      popular: false
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-cyan-800 to-blue-800 relative overflow-x-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-cyan-500/20 to-blue-700/20"></div>
      <div className="absolute top-20 left-10 w-64 h-64 bg-cyan-400/10 rounded-full blur-3xl"></div>
      <div className="absolute bottom-20 right-10 w-80 h-80 bg-blue-400/10 rounded-full blur-3xl"></div>
      <div className="absolute top-1/2 left-1/4 w-48 h-48 bg-cyan-300/10 rounded-full blur-2xl"></div>

      {/* Navigation */}
      <nav className="relative z-20 container mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-white text-xl">AI Assistant</span>
          </div>
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              onClick={onLogin}
              className="text-white hover:bg-white/10"
            >
              Sign In
            </Button>
            <Button
              onClick={onGetStarted}
              className="bg-cyan-600 hover:bg-cyan-500 text-white border-0"
            >
              Get Started
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 container mx-auto px-4 py-20 lg:py-32">
        <div className="max-w-4xl mx-auto text-center">
          <Badge className="mb-6 bg-cyan-500/20 text-cyan-200 border-cyan-400/30">
            ✨ Powered by Advanced AI
          </Badge>
          <h1 className="text-4xl lg:text-6xl text-white mb-6">
            Your Intelligent
            <br />
            <span className="bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              AI Companion
            </span>
          </h1>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            Experience the future of AI interaction with voice-enabled conversations, 
            smart quick actions, and a beautiful holographic interface
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Button
              onClick={onGetStarted}
              size="lg"
              className="bg-cyan-600 hover:bg-cyan-500 text-white border-0 px-8 py-6 text-lg rounded-full shadow-2xl"
            >
              Start Free Today
              <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="border-white/30 text-white hover:bg-white/10 px-8 py-6 text-lg rounded-full"
            >
              Watch Demo
            </Button>
          </div>

          {/* Holographic Globe Preview */}
          <div className="mt-16 relative">
            <div className="w-48 h-48 lg:w-64 lg:h-64 mx-auto relative">
              <div className="w-full h-full rounded-full relative overflow-hidden">
                <div className="absolute inset-0 rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 opacity-90"></div>
                <div className="absolute inset-0 rounded-full bg-gradient-to-br from-white/40 via-transparent to-transparent"></div>
                <div className="absolute inset-0 rounded-full bg-gradient-to-r from-transparent via-pink-300/30 to-transparent animate-[shimmer_3s_ease-in-out_infinite]"></div>
                <div className="absolute inset-4 rounded-full bg-gradient-radial from-white/20 to-transparent"></div>
              </div>
              <div className="absolute inset-[-20px] bg-gradient-to-r from-cyan-400/30 via-blue-400/30 to-purple-400/30 rounded-full blur-2xl"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative z-10 container mx-auto px-4 py-20">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl text-white mb-4">
              Powerful Features
            </h2>
            <p className="text-xl text-blue-200">
              Everything you need for intelligent AI conversations
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <Card
                key={index}
                className="p-6 backdrop-blur-lg bg-white/10 border-white/20 hover:bg-white/15 transition-all"
              >
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center mb-4 text-white">
                  {feature.icon}
                </div>
                <h3 className="text-xl text-white mb-2">{feature.title}</h3>
                <p className="text-blue-200">{feature.description}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="relative z-10 container mx-auto px-4 py-20">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl text-white mb-4">
              Simple Pricing
            </h2>
            <p className="text-xl text-blue-200">
              Choose the plan that works for you
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {plans.map((plan, index) => (
              <Card
                key={index}
                className={`p-8 backdrop-blur-lg border-2 transition-all relative ${
                  plan.popular
                    ? 'bg-cyan-500/20 border-cyan-400 shadow-2xl scale-105'
                    : 'bg-white/10 border-white/20 hover:bg-white/15'
                }`}
              >
                {plan.popular && (
                  <Badge className="absolute top-4 right-4 bg-cyan-500 text-white border-0">
                    Popular
                  </Badge>
                )}
                <h3 className="text-2xl text-white mb-2">{plan.name}</h3>
                <div className="mb-6">
                  <span className="text-4xl text-white">{plan.price}</span>
                  <span className="text-blue-200 ml-2">/ {plan.period}</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-blue-100">
                      <Check className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
                <Button
                  onClick={onGetStarted}
                  className={`w-full ${
                    plan.popular
                      ? 'bg-cyan-600 hover:bg-cyan-500'
                      : 'bg-blue-600 hover:bg-blue-500'
                  } text-white border-0`}
                >
                  {plan.cta}
                </Button>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 container mx-auto px-4 py-20">
        <Card className="max-w-4xl mx-auto p-12 backdrop-blur-lg bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border-cyan-400/30 text-center">
          <h2 className="text-3xl lg:text-4xl text-white mb-4">
            Ready to Get Started?
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            Join thousands of users already experiencing the future of AI
          </p>
          <Button
            onClick={onGetStarted}
            size="lg"
            className="bg-cyan-600 hover:bg-cyan-500 text-white border-0 px-8 py-6 text-lg rounded-full shadow-2xl"
          >
            Create Free Account
            <ArrowRight className="ml-2 w-5 h-5" />
          </Button>
        </Card>
      </section>

      {/* Footer */}
      <footer className="relative z-10 container mx-auto px-4 py-8 border-t border-white/10">
        <div className="text-center text-blue-200">
          <p>&copy; 2025 AI Assistant. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
