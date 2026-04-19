/** @jsxImportSource react */
import * as React from 'react';
import { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card } from './ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog';
import { ScrollArea } from './ui/scroll-area';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import { Slider } from './ui/slider';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Separator } from './ui/separator';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Mic, MicOff, Send, Settings, Menu, X, MessageSquare, Zap, Volume2, User, History, Trash2, Download, Moon, Sun, Clock,Paperclip,Search,Pencil,Star } from 'lucide-react';
import { toast } from 'sonner';
import { createId, createInitials } from '../lib/app-utils';
import { usePyBridge } from '../hooks/usePyBridge';

type ContentType='normal'|'code'|'content'|'technical'|'system';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  contentType?: ContentType;
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  titleLocked?: boolean;
  createdAt: Date;
  updatedAt: Date;
}

interface VoiceSettings {
  rate: number;
  pitch: number;
  volume: number;
  autoSpeak: boolean;
}

interface UserProfile {
  name: string;
  email?: string;
  avatar: string;
  initials: string;
}

interface AppSettings {
  theme: 'light' | 'dark' | 'auto';
  language: string;
  voiceSettings: VoiceSettings;
}

interface ResponsiveAIAssistantProps {
  authenticatedUser?: {
    email: string;
    name: string;
  } | null;
}

interface ConnectionBanner {
  type: 'warning' | 'success' | 'error';
  message: string;
  visible: boolean;
}

const QUICK_ACTIONS = [
  { id: 1, label: 'Tell me a joke', prompt: 'Tell me a funny joke', icon: '😄' },
  { id: 2, label: 'Explain AI', prompt: 'Explain artificial intelligence in simple terms', icon: '🤖' },
  { id: 3, label: 'Get inspired', prompt: 'Give me an inspirational quote', icon: '✨' },
  { id: 4, label: 'Help me focus', prompt: 'Give me productivity tips', icon: '🎯' },
  { id: 5, label: 'Fun fact', prompt: 'Tell me an interesting fun fact', icon: '💡' },
  { id: 6, label: 'Daily motivation', prompt: 'Give me daily motivation', icon: '🚀' },
];

function readLocalStorage<T>(key: string): T | null {
  try {
    const rawValue = localStorage.getItem(key);
    return rawValue ? (JSON.parse(rawValue) as T) : null;
  } catch (error) {
    console.warn(`Unable to parse localStorage key "${key}".`, error);
    localStorage.removeItem(key);
    return null;
  }
}

function writeLocalStorage(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.warn(`Unable to write localStorage key "${key}".`, error);
  }
}

export function ResponsiveAIAssistant({ authenticatedUser = null }: ResponsiveAIAssistantProps) {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(false);
  const [showAttachmentMenu, setShowAttachmentMenu] = useState(false);
  const [historySearch, setHistorySearch] = useState('');
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [connectionBanner, setConnectionBanner] = useState<ConnectionBanner>({
    type: 'warning',
    message: 'Checking connection...',
    visible: false
  });
  const { isConnected, sendMessageToPy } = usePyBridge();
  
  const [recognition, setRecognition] = useState<any>(null);
  const [speechSynthesis, setSpeechSynthesis] = useState<SpeechSynthesis | null>(null);
  
  const [userProfile, setUserProfile] = useState<UserProfile>({
    name: 'Guest User',
    avatar: '',
    initials: 'GU'
  });

  const [settings, setSettings] = useState<AppSettings>({
    theme: 'dark',
    language: 'en-US',
    voiceSettings: {
      rate: 0.9,
      pitch: 1,
      volume: 1,
      autoSpeak: false
    }
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const connectionHideTimerRef = useRef<number | null>(null);
  const responseTimerIdsRef = useRef<number[]>([]);
  const chatSessionsRef = useRef<ChatSession[]>([]);
  const currentSessionIdRef = useRef<string | null>(null);
  const messagesRef = useRef<Message[]>([]);

  // Load data from localStorage on mount
  useEffect(() => {
    const savedProfile = readLocalStorage<UserProfile>('userProfile');
    if (savedProfile) {
      setUserProfile((prev) => ({
        ...prev,
        ...savedProfile,
        initials: savedProfile.initials || createInitials(savedProfile.name ?? prev.name),
      }));
    }

    const savedSettings = readLocalStorage<AppSettings>('appSettings');
    if (savedSettings) {
      setSettings((prev) => ({
        ...prev,
        ...savedSettings,
        voiceSettings: {
          ...prev.voiceSettings,
          ...savedSettings.voiceSettings,
        },
      }));
    }

    const savedSessions = readLocalStorage<ChatSession[]>('chatSessions');
    if (Array.isArray(savedSessions)) {
      // Convert date strings back to Date objects
      const parsedSessions = savedSessions.map((session: any) => ({
        ...session,
        createdAt: new Date(session.createdAt || Date.now()),
        updatedAt: new Date(session.updatedAt || Date.now()),
        messages: Array.isArray(session.messages) ? session.messages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp || Date.now())
        })) : []
      }));
      chatSessionsRef.current = parsedSessions;
      setChatSessions(parsedSessions);
    }
  }, []);

  useEffect(() => {
    currentSessionIdRef.current = currentSessionId;
  }, [currentSessionId]);

  useEffect(() => {
    chatSessionsRef.current = chatSessions;
  }, [chatSessions]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    if (!authenticatedUser) {
      return;
    }

    setUserProfile((prev) => {
      const nextName = authenticatedUser.name.trim() || prev.name;
      return {
        ...prev,
        name: nextName,
        email: authenticatedUser.email,
        initials: createInitials(nextName, prev.initials),
      };
    });
  }, [authenticatedUser]);

  // Save to localStorage when data changes
  useEffect(() => {
    writeLocalStorage('userProfile', userProfile);
  }, [userProfile]);

  useEffect(() => {
    writeLocalStorage('appSettings', settings);
  }, [settings]);

  useEffect(() => {
    writeLocalStorage('chatSessions', chatSessions);
  }, [chatSessions]);

  useEffect(() => {
    // Initialize speech recognition
    let recognitionInstance: any = null;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      recognitionInstance = new SpeechRecognition();
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = settings.language;

      recognitionInstance.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        setInputText(transcript);
        setIsListening(false);
        toast.success('Voice recognized!');
      };

      recognitionInstance.onerror = () => {
        setIsListening(false);
        toast.error('Voice recognition error');
      };

      recognitionInstance.onend = () => {
        setIsListening(false);
      };

      setRecognition(recognitionInstance);
    } else {
      setRecognition(null);
    }

    // Initialize speech synthesis
    if ('speechSynthesis' in window) {
      setSpeechSynthesis(window.speechSynthesis);
    } else {
      setSpeechSynthesis(null);
    }

    return () => {
      recognitionInstance?.stop();
      window.speechSynthesis?.cancel();
    };
  }, [settings.language]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    return () => {
      responseTimerIdsRef.current.forEach((timerId) => window.clearTimeout(timerId));
      responseTimerIdsRef.current = [];
    };
  }, []);

  useEffect(function () {
    function clearBannerTimer() {
      if (connectionHideTimerRef.current !== null) {
        window.clearTimeout(connectionHideTimerRef.current);
        connectionHideTimerRef.current = null;
      }
    }
    
    function showOnline() {
      clearBannerTimer();
      setConnectionBanner({ type: 'success', message: 'Online', visible: true });
      connectionHideTimerRef.current = window.setTimeout(function () {
        setConnectionBanner(function (prev) {
          return { ...prev, visible: false };
        });
      }, 4000);
    }
    
    function showOffline() {
      clearBannerTimer();
      setConnectionBanner({ type: 'error', message: 'Offline - check your connection', visible: true });
    }
    
    function updateStatus() {
      if (navigator.onLine) {
        showOnline();
      } else {
        showOffline();
      }
    }
    
    updateStatus();
    window.addEventListener('online', updateStatus);
    window.addEventListener('offline', updateStatus);
    
    return function () {
      window.removeEventListener('online', updateStatus);
      window.removeEventListener('offline', updateStatus);
      clearBannerTimer();
    };
  }, []);

  const generateAIResponse = (userMessage: string): string => {
    const lowerMessage = userMessage.toLowerCase();
    
    if (lowerMessage.includes('hello') || lowerMessage.includes('hi')) {
      return `Hello ${userProfile.name}! I'm your AI assistant. I'm here to help you with anything you need. How can I assist you today?`;
    } else if (lowerMessage.includes('weather')) {
      return "I'd love to help with weather information! In a full implementation, I'd connect to a weather API to give you current conditions for your location.";
    } else if (lowerMessage.includes('time')) {
      return `The current time is ${new Date().toLocaleTimeString()}.`;
    } else if (lowerMessage.includes('help')) {
      return "I'm here to help! You can ask me questions, have a conversation, or use voice input by tapping the microphone button. Try the Quick Actions for some ideas!";
    } else if (lowerMessage.includes('joke')) {
      return "Why did the AI go to therapy? Because it had too many deep learning issues! 😄";
    } else if (lowerMessage.includes('ai') || lowerMessage.includes('artificial intelligence')) {
      return "Artificial Intelligence (AI) is technology that enables computers to simulate human intelligence - learning from experience, understanding language, recognizing patterns, and making decisions. Think of it as teaching computers to think and learn like humans do!";
    } else if (lowerMessage.includes('inspire') || lowerMessage.includes('quote')) {
      return "Here's an inspiring quote: 'The future belongs to those who believe in the beauty of their dreams.' - Eleanor Roosevelt ✨";
    } else if (lowerMessage.includes('productivity') || lowerMessage.includes('focus')) {
      return "Here are some productivity tips: 1) Use the Pomodoro Technique (25 min work, 5 min break), 2) Prioritize your top 3 tasks each day, 3) Minimize distractions by turning off notifications, 4) Take regular breaks to recharge! 🎯";
    } else if (lowerMessage.includes('fun fact') || lowerMessage.includes('fact')) {
      return "Fun fact: Honey never spoils! Archaeologists have found 3,000-year-old honey in Egyptian tombs that was still perfectly edible. 🍯";
    } else if (lowerMessage.includes('motivat')) {
      return "You've got this! 💪 Every small step you take today brings you closer to your goals. Believe in yourself and keep moving forward. You're capable of amazing things! 🚀";
    } else {
      return "That's an interesting question! I'm a demo AI assistant with simulated responses, but I'm designed to show how voice and chat interactions work together. Try asking me about jokes, AI, inspiration, or use the Quick Actions menu!";
    }
  };

  const replaceChatSessions = (updater: (prev: ChatSession[]) => ChatSession[]) => {
    setChatSessions((prev) => {
      const next = updater(prev);
      chatSessionsRef.current = next;
      return next;
    });
  };

  const commitMessages = (nextMessages: Message[]) => {
    messagesRef.current = nextMessages;
    setMessages(nextMessages);
  };

  const getSessionMessages = (sessionId: string) => {
    return (
      chatSessionsRef.current.find((session) => session.id === sessionId)?.messages ??
      (currentSessionIdRef.current === sessionId ? messagesRef.current : [])
    );
  };

  const ensureSession = (initialText: string) => {
    if (currentSessionIdRef.current) {
      return currentSessionIdRef.current;
    }

    const newSession: ChatSession = {
      id: createId(),
      title: initialText.slice(0, 30) + (initialText.length > 30 ? '...' : ''),
      messages: [],
      titleLocked: false,
      createdAt: new Date(),
      updatedAt: new Date()
    };

    currentSessionIdRef.current = newSession.id;
    setCurrentSessionId(newSession.id);
    replaceChatSessions((prev) => [newSession, ...prev]);
    return newSession.id;
  };

  const createNewSession = () => {
    const newSession: ChatSession = {
      id: createId(),
      title: 'New Chat',
      messages: [],
      titleLocked: false,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    currentSessionIdRef.current = newSession.id;
    replaceChatSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
    commitMessages([]);
    setShowChat(true);
    toast.success('New chat started');
  };

  const loadSession = (sessionId: string) => {
    const session = chatSessions.find(s => s.id === sessionId);
    if (session) {
      currentSessionIdRef.current = sessionId;
      setCurrentSessionId(sessionId);
      commitMessages(session.messages);
      setShowChat(true);
      setShowHistory(false);
      setShowSidebar(false);
      setShowAttachmentMenu(false);
    }
  };

  const deleteSession = (sessionId: string) => {
    replaceChatSessions((prev) => prev.filter((session) => session.id !== sessionId));
    if (currentSessionIdRef.current === sessionId) {
      currentSessionIdRef.current = null;
      setCurrentSessionId(null);
      commitMessages([]);
      setShowChat(false);
    }
    toast.success('Chat deleted');
  };

  const renameSession = (sessionId: string) => {
    const session = chatSessions.find(s => s.id === sessionId);
    const currentTitle = session ? session.title : 'Chat';
    const newTitle = window.prompt('Rename chat', currentTitle);
    const trimmedTitle = newTitle?.trim();
    if (!trimmedTitle) return;
    replaceChatSessions((prev) =>
      prev.map((session) =>
        session.id === sessionId
          ? { ...session, title: trimmedTitle, titleLocked: true, updatedAt: new Date() }
          : session
      )
    );
    toast.success('Chat renamed');
  };

  const clearAllHistory = () => {
    currentSessionIdRef.current = null;
    replaceChatSessions(() => []);
    setCurrentSessionId(null);
    commitMessages([]);
    setShowChat(false);
    setShowHistory(false);
    toast.success('All chat history cleared');
  };

  const updateCurrentSession = (sessionId: string, newMessages: Message[]) => {
    replaceChatSessions((prev) =>
      prev.map((session) => {
        if (session.id !== sessionId) {
          return session;
        }

        const firstUserMessage = newMessages.find((message) => message.sender === 'user');
        const title = firstUserMessage
          ? firstUserMessage.text.slice(0, 30) + (firstUserMessage.text.length > 30 ? '...' : '')
          : 'New Chat';

        return {
          ...session,
          title: session.titleLocked ? session.title : title,
          messages: newMessages,
          updatedAt: new Date()
        };
      })
    );
  };

  const inferContentType = (text: string) => {
    const trimmed = text.trim();
    if (trimmed.startsWith('```') || trimmed.includes('```')) return 'code';
    if (/system:/i.test(trimmed)) return 'system';
    if (/(error|exception|traceback|stack)/i.test(text)) return 'technical';
    if (trimmed.length > 280) return 'content';
    return 'normal';
  };

  const getContentTypeTone = (type: string) => {
    switch (type) {
      case 'code':
        return 'ring-1 ring-slate-400/40';
      case 'technical':
        return 'ring-1 ring-amber-400/40';
      case 'system':
        return 'ring-1 ring-gray-400/40';
      case 'content':
        return 'ring-1 ring-blue-400/40';
      default:
        return '';
    }
  };
  
  const getContentTypeLabel = (type: string) => {
    switch (type) {
      case 'code':
        return 'Code';
      case 'technical':
        return 'Technical';
      case 'system':
        return 'System';
      case 'content':
        return 'Content';
      default:
        return '';
    }
  };

  const handleSendMessage = async (messageText?: string) => {
    const textToSend = (messageText ?? inputText).trim();
    if (!textToSend) return;

    const sessionId = ensureSession(textToSend);
    const userMessage: Message = {
      id: createId(),
      text: textToSend,
      sender: 'user',
      contentType: inferContentType(textToSend),
      timestamp: new Date()
    };

    const nextMessages = [...getSessionMessages(sessionId), userMessage];
    updateCurrentSession(sessionId, nextMessages);
    if (currentSessionIdRef.current === sessionId) {
      commitMessages(nextMessages);
    }
    setShowChat(true);
    setInputText('');
    setShowQuickActions(false);
    setShowAttachmentMenu(false);

    if (isConnected && window.pyBridge) {
      try {
        const rawResponse = await sendMessageToPy(textToSend);
        let responseText = "";
        let responseContentType: ContentType = "normal";

        try {
          // Parse the JSON coming from PySide6 process_message
          const parsed = JSON.parse(rawResponse);
          responseText = parsed.response || rawResponse;
          responseContentType = (parsed.content_type as ContentType) || inferContentType(responseText);
        } catch (e) {
          responseText = rawResponse;
          responseContentType = inferContentType(responseText);
        }

        const aiResponse: Message = {
          id: createId(),
          text: responseText,
          sender: 'ai',
          contentType: responseContentType,
          timestamp: new Date()
        };

        const updatedMessages = [...getSessionMessages(sessionId), aiResponse];
        updateCurrentSession(sessionId, updatedMessages);
        if (currentSessionIdRef.current === sessionId) {
          commitMessages(updatedMessages);
        }

        if (settings.voiceSettings.autoSpeak) {
          handleSpeak(responseText);
        }
      } catch (error) {
        const errorResponse: Message = {
          id: createId(),
          text: "Error: Could not reach Python backend. " + (error instanceof Error ? error.message : ""),
          sender: 'ai',
          contentType: 'system',
          timestamp: new Date()
        };
        const updatedMessages = [...getSessionMessages(sessionId), errorResponse];
        updateCurrentSession(sessionId, updatedMessages);
        if (currentSessionIdRef.current === sessionId) {
          commitMessages(updatedMessages);
        }
      }
    } else {
      // Fallback to mock text if not running inside the desktop app wrapper
      const responseTimerId = window.setTimeout(() => {
        const aiResponseText = generateAIResponse(textToSend);
        const aiResponse: Message = {
          id: createId(),
          text: aiResponseText,
          sender: 'ai',
          contentType: inferContentType(aiResponseText),
          timestamp: new Date()
        };
        const updatedMessages = [...getSessionMessages(sessionId), aiResponse];
        updateCurrentSession(sessionId, updatedMessages);
        if (currentSessionIdRef.current === sessionId) {
          commitMessages(updatedMessages);
        }

        if (settings.voiceSettings.autoSpeak) {
          handleSpeak(aiResponseText);
        }

        responseTimerIdsRef.current = responseTimerIdsRef.current.filter((timerId) => timerId !== responseTimerId);
      }, 1000);

      responseTimerIdsRef.current.push(responseTimerId);
    }
  };

  const handleQuickAction = (prompt: string) => {
    setInputText(prompt);
    handleSendMessage(prompt);
  };

  const handleVoiceInput = () => {
    if (!recognition) {
      toast.error('Speech recognition is not supported in your browser.');
      return;
    }

    if (isListening) {
      recognition.stop();
      setIsListening(false);
    } else {
      try {
        recognition.start();
        setIsListening(true);
        toast.info('Listening...');
      } catch (err) {
        console.error('Speech recognition start error:', err);
        setIsListening(false);
      }
    }
  };

  const handleSpeak = (text: string) => {
    if (!speechSynthesis) {
      toast.error('Speech synthesis is not supported in your browser.');
      return;
    }

    if (isSpeaking) {
      speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = settings.voiceSettings.rate;
    utterance.pitch = settings.voiceSettings.pitch;
    utterance.volume = settings.voiceSettings.volume;
    
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
  };

  const handleAttachmentClick = (accept = '') => {
    const inputEl = fileInputRef.current;
    if (!inputEl) return;
    inputEl.accept = accept;
    inputEl.click();
    setShowAttachmentMenu(false);
  };
  
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const fileNames = Array.from(files).map((file) => file.name).join(', ');
    toast.success('Attached: '+ fileNames);
    e.target.value = '';
  };
  
  const handleRateMessage = (messageId: string, rating: number) => {
    setRatings(prev => ({ ...prev, [messageId]: rating }));
    toast.success('Thanks for rating');
  };

  const exportChatHistory = () => {
    const dataStr = JSON.stringify(chatSessions, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `chat-history-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    toast.success('Chat history exported');
  };

  const filteredSessions = chatSessions.filter(session => {
    if (!historySearch.trim()) return true;
    const q = historySearch.toLowerCase();
    return session.title.toLowerCase().includes(q) || session.messages.some(m => m.text.toLowerCase().includes(q));
  });

  const connectionBannerStyles = connectionBanner.type === 'success'
    ? {
      container: 'bg-emerald-500/20 text-emerald-200 border-emerald-400/40',
      dot: 'bg-emerald-400'
    }
    : connectionBanner.type === 'error'
    ? {
      container: 'bg-red-500/20 text-red-200 border-red-400/40',
      dot: 'bg-red-400'
    }
    : {
      container: 'bg-yellow-500/20 text-yellow-200 border-yellow-400/40',
      dot: 'bg-yellow-400'
    };

  return (
    <div className="h-screen bg-gradient-to-br from-blue-900 via-cyan-800 to-blue-800 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-cyan-500/20 to-blue-700/20"></div>
      <div className="absolute top-20 left-10 w-32 h-32 bg-cyan-400/10 rounded-full blur-xl"></div>
      <div className="absolute bottom-20 right-10 w-40 h-40 bg-blue-400/10 rounded-full blur-xl"></div>
      <div className="absolute top-1/2 left-1/4 w-24 h-24 bg-cyan-300/10 rounded-full blur-lg"></div>

      {connectionBanner.visible && (
        <div className={"fixed top-4 right-4 z-50 px-4 py-2 rounded-full text-sm border shadow-lg backdrop-blur-lg " + connectionBannerStyles.container}>
          {connectionBanner.message}
        </div>
      )}

      {/* Mobile Sidebar Overlay */}
      {showSidebar && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setShowSidebar(false)}>
          <div className="absolute right-0 top-0 h-full w-80 bg-gray-900/95 backdrop-blur-lg border-l border-gray-700" onClick={(e) => e.stopPropagation()}>
            <div className="p-6">
              <div className="flex items-center justify-between mb-8">
                <h3 className="text-white">Menu</h3>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setShowSidebar(false)}
                  className="text-white hover:bg-gray-800"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
              
              <div className="space-y-3">
                <Button 
                  variant="ghost" 
                  className="w-full justify-start text-white hover:bg-gray-800"
                  onClick={() => {
                    setShowHistory(true);
                    setShowSidebar(false);
                  }}
                >
                  <History className="w-4 h-4 mr-3" />
                  Chat History
                </Button>
                <Button 
                  variant="ghost" 
                  className="w-full justify-start text-white hover:bg-gray-800"
                  onClick={() => {
                    setShowQuickActions(!showQuickActions);
                  }}
                >
                  <Zap className="w-4 h-4 mr-3" />
                  Quick Actions
                </Button>
                <Button 
                  variant="ghost" 
                  className="w-full justify-start text-white hover:bg-gray-800"
                  onClick={() => {
                    setShowSettings(true);
                    setShowSidebar(false);
                  }}
                >
                  <Settings className="w-4 h-4 mr-3" />
                  Settings
                </Button>
                <Button 
                  variant="ghost" 
                  className="w-full justify-start text-white hover:bg-gray-800"
                  onClick={() => {
                    setShowProfile(true);
                    setShowSidebar(false);
                  }}
                >
                  <User className="w-4 h-4 mr-3" />
                  Profile
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Desktop Sidebar */}
      <div className="hidden lg:block fixed left-0 top-0 h-full w-64 bg-gray-900/30 backdrop-blur-lg border-r border-gray-700/50 z-30">
        <div className="p-6 flex flex-col h-full">
          <div className="mb-8">
            <h2 className="text-white mb-2">AI Assistant</h2>
            <p className="text-cyan-300 text-sm">Your intelligent companion</p>
          </div>
          
          <Button 
            onClick={createNewSession}
            className="w-full mb-6 bg-cyan-600 hover:bg-cyan-500 text-white border-0"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            New Chat
          </Button>
          
          <div className="space-y-3 flex-1 overflow-y-auto">
            <Button 
              variant="ghost" 
              className="w-full justify-start text-white hover:bg-gray-800/50"
              onClick={() => setShowHistory(true)}
            >
              <History className="w-4 h-4 mr-3" />
              Chat History
            </Button>
            <Button 
              variant="ghost" 
              className="w-full justify-start text-white hover:bg-gray-800/50"
              onClick={() => setShowQuickActions(!showQuickActions)}
            >
              <Zap className="w-4 h-4 mr-3" />
              Quick Actions
            </Button>
            <Button 
              variant="ghost" 
              className="w-full justify-start text-white hover:bg-gray-800/50"
              onClick={() => setShowSettings(true)}
            >
              <Settings className="w-4 h-4 mr-3" />
              Settings
            </Button>
            <Button 
              variant="ghost" 
              className="w-full justify-start text-white hover:bg-gray-800/50"
              onClick={() => setShowProfile(true)}
            >
              <User className="w-4 h-4 mr-3" />
              Profile
            </Button>
          </div>

          <Separator className="my-4 bg-gray-700/50" />

          <div className="flex items-center gap-3 mt-auto">
            <Avatar>
              <AvatarImage src={userProfile.avatar} />
              <AvatarFallback className="bg-cyan-600 text-white">
                {userProfile.initials}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm truncate">{userProfile.name}</p>
              <p className="text-cyan-300 text-xs">Online</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-col h-full lg:ml-64">
        {/* Header */}
        <div className="flex items-center justify-between p-4 lg:p-6 relative z-20">
          <div className="flex items-center gap-3">
            <Button 
              variant="ghost" 
              size="sm" 
              className="lg:hidden text-white hover:bg-white/10"
              onClick={() => setShowSidebar(true)}
            >
              <Menu className="w-5 h-5" />
            </Button>
            <h1 className="text-white">AI Assistant</h1>
            {currentSessionId && (
              <Badge variant="outline" className="text-cyan-300 border-cyan-300/50 hidden sm:inline-flex">
                Active Chat
              </Badge>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {showChat && (
              <Button 
                variant="ghost" 
                size="sm" 
                className="text-white hover:bg-white/10"
                onClick={createNewSession}
              >
                <MessageSquare className="w-5 h-5" />
              </Button>
            )}
          </div>
        </div>

        {/* Quick Actions Panel */}
        {showQuickActions && (
          <div className="mx-4 lg:mx-6 mb-4 relative z-20">
            <Card className="backdrop-blur-lg bg-white/10 border border-white/20 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-white">Quick Actions</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowQuickActions(false)}
                  className="text-white hover:bg-white/10 h-6 w-6 p-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {QUICK_ACTIONS.map(action => (
                  <Button
                    key={action.id}
                    variant="outline"
                    className="justify-start text-white border-white/20 hover:bg-white/10 h-auto py-3"
                    onClick={() => handleQuickAction(action.prompt)}
                  >
                    <span className="mr-2">{action.icon}</span>
                    <span className="text-xs">{action.label}</span>
                  </Button>
                ))}
              </div>
            </Card>
          </div>
        )}

        {/* Content Area */}
        <div className="flex-1 relative z-10 px-4 lg:px-6 overflow-hidden">
          {!showChat ? (
            /* Welcome Screen */
            <div className="flex flex-col items-center justify-center h-full text-center space-y-6 lg:space-y-8">
              {/* Globe */}
              <div className="relative">
                <div className="w-32 h-32 lg:w-48 lg:h-48 relative">
                  {/* Holographic Orb */}
                  <div className="w-full h-full rounded-full relative overflow-hidden">
                    {/* Main sphere gradient */}
                    <div className="absolute inset-0 rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 opacity-90"></div>
                    
                    {/* Glossy highlight */}
                    <div className="absolute inset-0 rounded-full bg-gradient-to-br from-white/40 via-transparent to-transparent"></div>
                    
                    {/* Holographic shimmer effect */}
                    <div className="absolute inset-0 rounded-full bg-gradient-to-r from-transparent via-pink-300/30 to-transparent animate-[shimmer_3s_ease-in-out_infinite]"></div>
                    
                    {/* Inner glow */}
                    <div className="absolute inset-4 rounded-full bg-gradient-radial from-white/20 to-transparent"></div>
                  </div>
                  
                  {/* Animated rings when active */}
                  {(isListening || isSpeaking) && (
                    <>
                      <div className="absolute inset-0 rounded-full border-4 border-cyan-400 animate-ping"></div>
                      <div className="absolute inset-[-8px] rounded-full border-2 border-cyan-300/50 animate-pulse"></div>
                    </>
                  )}
                  
                  {/* Outer glow */}
                  <div className="absolute inset-[-20px] bg-gradient-to-r from-cyan-400/30 via-blue-400/30 to-purple-400/30 rounded-full blur-2xl"></div>
                </div>
              </div>

              {/* Welcome Text */}
              <div className="space-y-2 lg:space-y-4">
                <h2 className="text-white">Hello {userProfile.name}!</h2>
                <p className="text-cyan-200">I'm your AI assistant</p>
                <p className="text-blue-200 max-w-md">
                  Ready to help you with questions, tasks, and conversations
                </p>
              </div>

              {/* Quick Action Buttons */}
              <div className="flex flex-wrap gap-3 lg:gap-4 justify-center max-w-lg">
                <Button
                  onClick={createNewSession}
                  className="bg-cyan-600 hover:bg-cyan-500 text-white border-0 px-6 py-3 rounded-full shadow-lg"
                >
                  <MessageSquare className="w-4 h-4 mr-2" />
                  Start Chat
                </Button>
                <Button
                  onClick={handleVoiceInput}
                  className={`${isListening ? 'bg-red-600 hover:bg-red-500' : 'bg-blue-600 hover:bg-blue-500'} text-white border-0 px-6 py-3 rounded-full shadow-lg`}
                >
                  {isListening ? <MicOff className="w-4 h-4 mr-2" /> : <Mic className="w-4 h-4 mr-2" />}
                  {isListening ? 'Stop' : 'Voice'}
                </Button>
                <Button
                  onClick={() => setShowQuickActions(!showQuickActions)}
                  className="bg-purple-600 hover:bg-purple-500 text-white border-0 px-6 py-3 rounded-full shadow-lg"
                >
                  <Zap className="w-4 h-4 mr-2" />
                  Quick Actions
                </Button>
              </div>
            </div>
          ) : (
            /* Chat Interface */
            <div className="h-full flex flex-col">
              {/* Chat Messages */}
              <ScrollArea className="flex-1 pr-4">
                <div className="space-y-4 pb-4">
                  {messages.length === 0 && (
                    <div className="text-center py-8">
                      <p className="text-cyan-200">Start a conversation...</p>
                    </div>
                  )}
                  
                  {messages.map((message) => {
                    const contentType = message.contentType || inferContentType(message.text);
                    const rating = ratings[message.id] || 0;
                    const typeTone = getContentTypeTone(contentType);
                    const typeLabel = getContentTypeLabel(contentType);
                    return (
                    <div
                      key={message.id}
                      className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <Card className={`max-w-[85%] lg:max-w-[70%] p-4 backdrop-blur-lg border-0 shadow-xl ${typeTone} ${
                        message.sender === 'user' 
                          ? 'bg-cyan-600/80 text-white' 
                          : 'bg-white/10 text-white border border-white/20'
                      }`}>
                        {typeLabel && (
                          <Badge className="mb-2 bg-white/10 text-white border-white/20">{typeLabel}</Badge>
                        )}
                        <div className="flex items-start justify-between gap-2">
                                                    {contentType === 'code' ? (
                            <pre className="text-sm font-mono whitespace-pre-wrap">{message.text}</pre>
                          ) : (
                            <p className="text-sm lg:text-base">{message.text}</p>
                          )}
{message.sender === 'ai' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="shrink-0 h-8 w-8 p-0 text-cyan-300 hover:bg-white/10"
                              onClick={() => handleSpeak(message.text)}
                            >
                              <Volume2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                        <p className="text-xs opacity-70 mt-2">
                          {message.timestamp.toLocaleTimeString()}
                        </p>
                        <div className="flex items-center gap-1 mt-3">
                          {[1,2,3,4,5].map((value) => (
                            <button key={message.id + '-' + value} onClick={() => handleRateMessage(message.id, value)} className="h-6 w-6 flex items-center justify-center rounded-full hover:bg-white/10">
                              <Star className={rating >= value ? 'h-4 w-4 fill-current text-yellow-300' : 'h-4 w-4 fill-current text-yellow-300/40'} />
                            </button>
                          ))}
                          <span className="text-xs text-white/60 ml-2">{rating ? rating + '/5' : 'Rate'}</span>
                        </div>
                      </Card>
                    </div>
                  )})}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>
            </div>
          )}
        </div>

        {/* Chat Input - Always at bottom */}
        <form 
          onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} 
          className="p-4 lg:p-6 relative z-20"
        >
          <Card className="backdrop-blur-lg bg-white/10 border border-white/20 p-4 shadow-xl">
            <div className="flex gap-3">
              <div className="relative">
                <Button type="button" variant="ghost" size="sm" className="h-10 w-10 p-0 text-cyan-200 hover:bg-white/10" onClick={() => setShowAttachmentMenu(!showAttachmentMenu)}>
                  <Paperclip className="h-4 w-4" />
                </Button>
                {showAttachmentMenu && (
                  <div className="absolute bottom-12 left-0 w-48 bg-gray-900/95 border border-gray-700 rounded-lg shadow-xl p-2 backdrop-blur-lg">
                    <button className="w-full text-left px-3 py-2 rounded-md text-sm text-white hover:bg-white/10" onClick={() => handleAttachmentClick('image/*')}>Image</button>
                    <button className="w-full text-left px-3 py-2 rounded-md text-sm text-white hover:bg-white/10" onClick={() => handleAttachmentClick('.pdf,.doc,.docx,.txt')}>Document</button>
                    <button className="w-full text-left px-3 py-2 rounded-md text-sm text-white hover:bg-white/10" onClick={() => handleAttachmentClick('.csv,.json,.xlsx')}>Data</button>
                    <button className="w-full text-left px-3 py-2 rounded-md text-sm text-white hover:bg-white/10" onClick={() => handleAttachmentClick()}>Any file</button>
                  </div>
                )}
                <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileSelect} multiple />
              </div>
              <div className="flex-1 relative">
                  <Input
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Type your message..."
                    className="bg-white/10 border-white/20 text-white placeholder:text-white/60 pr-12 rounded-full focus:ring-2 focus:ring-cyan-400 focus:border-transparent"
                  />
                <Button
                    type="button"
                  variant="ghost"
                  size="sm"
                  className={`absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 p-0 ${
                    isListening ? 'text-red-400' : 'text-cyan-300'
                  } hover:bg-white/10`}
                  onClick={handleVoiceInput}
                >
                  {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                </Button>
              </div>
              <Button 
                type="submit"
                disabled={!inputText.trim()}
                className="bg-cyan-600 hover:bg-cyan-500 text-white border-0 rounded-full px-6 shadow-lg disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            
            {isListening && (
              <div className="mt-3 text-center">
                <div className="text-sm text-cyan-300 animate-pulse flex items-center justify-center gap-2">
                  <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce"></span>
                  Listening... Speak now
                  <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                </div>
              </div>
            )}
            
            {isSpeaking && (
              <div className="mt-3 text-center">
                <p className="text-sm text-blue-300 animate-pulse flex items-center justify-center gap-2">
                  <Volume2 className="w-4 h-4" />
                  Speaking...
                </p>
              </div>
            )}
          </Card>
        </form>
      </div>

      {/* Settings Dialog */}
      <Dialog open={showSettings} onOpenChange={setShowSettings}>
        <DialogContent className="bg-gray-900/95 backdrop-blur-lg border-gray-700 text-white max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-white">Settings</DialogTitle>
            <DialogDescription className="text-gray-400">
              Customize your AI assistant experience
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="voice" className="w-full">
            <TabsList className="grid w-full grid-cols-2 bg-gray-800">
              <TabsTrigger value="voice">Voice</TabsTrigger>
              <TabsTrigger value="general">General</TabsTrigger>
            </TabsList>

            <TabsContent value="voice" className="space-y-6 mt-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-white">Auto-speak responses</Label>
                    <p className="text-sm text-gray-400">Automatically read AI responses aloud</p>
                  </div>
                  <Switch
                    checked={settings.voiceSettings.autoSpeak}
                    onCheckedChange={(checked: any) => 
                      setSettings(prev => ({
                        ...prev,
                        voiceSettings: { ...prev.voiceSettings, autoSpeak: checked }
                      }))
                    }
                  />
                </div>

                <Separator className="bg-gray-700" />

                <div className="space-y-3">
                  <Label className="text-white">Speech Rate: {settings.voiceSettings.rate.toFixed(1)}</Label>
                  <Slider
                    value={[settings.voiceSettings.rate]}
                    onValueChange={([value]: number[]) => 
                      setSettings(prev => ({
                        ...prev,
                        voiceSettings: { ...prev.voiceSettings, rate: value }
                      }))
                    }
                    min={0.5}
                    max={2}
                    step={0.1}
                    className="w-full"
                  />
                  <p className="text-sm text-gray-400">Adjust how fast the AI speaks</p>
                </div>

                <div className="space-y-3">
                  <Label className="text-white">Pitch: {settings.voiceSettings.pitch.toFixed(1)}</Label>
                  <Slider
                    value={[settings.voiceSettings.pitch]}
                    onValueChange={([value]: number[]) => 
                      setSettings(prev => ({
                        ...prev,
                        voiceSettings: { ...prev.voiceSettings, pitch: value }
                      }))
                    }
                    min={0.5}
                    max={2}
                    step={0.1}
                    className="w-full"
                  />
                  <p className="text-sm text-gray-400">Adjust voice pitch</p>
                </div>

                <div className="space-y-3">
                  <Label className="text-white">Volume: {Math.round(settings.voiceSettings.volume * 100)}%</Label>
                  <Slider
                    value={[settings.voiceSettings.volume]}
                    onValueChange={([value]: number[]) => 
                      setSettings(prev => ({
                        ...prev,
                        voiceSettings: { ...prev.voiceSettings, volume: value }
                      }))
                    }
                    min={0}
                    max={1}
                    step={0.1}
                    className="w-full"
                  />
                  <p className="text-sm text-gray-400">Adjust voice volume</p>
                </div>

                <Button
                  onClick={() => handleSpeak("This is a test of the current voice settings.")}
                  className="w-full bg-cyan-600 hover:bg-cyan-500"
                >
                  <Volume2 className="w-4 h-4 mr-2" />
                  Test Voice Settings
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="general" className="space-y-6 mt-6">
              <div className="space-y-4">
                <div>
                  <Label className="text-white mb-2 block">Language</Label>
                  <select
                    value={settings.language}
                    onChange={(e) => setSettings(prev => ({ ...prev, language: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="en-US">English (US)</option>
                    <option value="en-GB">English (UK)</option>
                    <option value="es-ES">Spanish</option>
                    <option value="fr-FR">French</option>
                    <option value="de-DE">German</option>
                    <option value="it-IT">Italian</option>
                    <option value="ja-JP">Japanese</option>
                    <option value="zh-CN">Chinese (Simplified)</option>
                  </select>
                  <p className="text-sm text-gray-400 mt-1">Select voice recognition language</p>
                </div>

                <Separator className="bg-gray-700" />

                <div>
                  <Label className="text-white mb-2 block">Theme</Label>
                  <div className="grid grid-cols-3 gap-3">
                    <Button
                      variant={settings.theme === 'dark' ? 'default' : 'outline'}
                      onClick={() => setSettings(prev => ({ ...prev, theme: 'dark' }))}
                      className={settings.theme === 'dark' ? 'bg-cyan-600' : 'border-gray-700 text-white'}
                    >
                      <Moon className="w-4 h-4 mr-2" />
                      Dark
                    </Button>
                    <Button
                      variant={settings.theme === 'light' ? 'default' : 'outline'}
                      onClick={() => setSettings(prev => ({ ...prev, theme: 'light' }))}
                      className={settings.theme === 'light' ? 'bg-cyan-600' : 'border-gray-700 text-white'}
                    >
                      <Sun className="w-4 h-4 mr-2" />
                      Light
                    </Button>
                    <Button
                      variant={settings.theme === 'auto' ? 'default' : 'outline'}
                      onClick={() => setSettings(prev => ({ ...prev, theme: 'auto' }))}
                      className={settings.theme === 'auto' ? 'bg-cyan-600' : 'border-gray-700 text-white'}
                    >
                      Auto
                    </Button>
                  </div>
                  <p className="text-sm text-gray-400 mt-1">Choose your preferred theme (coming soon)</p>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* Profile Dialog */}
      <Dialog open={showProfile} onOpenChange={setShowProfile}>
        <DialogContent className="bg-gray-900/95 backdrop-blur-lg border-gray-700 text-white">
          <DialogHeader>
            <DialogTitle className="text-white">Profile</DialogTitle>
            <DialogDescription className="text-gray-400">
              Manage your profile information
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6">
            <div className="flex flex-col items-center gap-4">
              <Avatar className="w-24 h-24">
                <AvatarImage src={userProfile.avatar} />
                <AvatarFallback className="bg-cyan-600 text-white text-2xl">
                  {userProfile.initials}
                </AvatarFallback>
              </Avatar>
              <Button variant="outline" className="border-gray-700 text-white hover:bg-gray-800">
                Change Avatar
              </Button>
            </div>

            <Separator className="bg-gray-700" />

            <div className="space-y-4">
              <div>
                <Label className="text-white mb-2 block">Name</Label>
                <Input
                  value={userProfile.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    const initials = name
                      .split(' ')
                      .map(n => n[0])
                      .join('')
                      .toUpperCase()
                      .slice(0, 2);
                    setUserProfile(prev => ({ ...prev, name, initials }));
                  }}
                  className="bg-gray-800 border-gray-700 text-white"
                  placeholder="Enter your name"
                />
              </div>

              <div>
                <Label className="text-white mb-2 block">Initials</Label>
                <Input
                  value={userProfile.initials}
                  onChange={(e) => 
                    setUserProfile(prev => ({ ...prev, initials: e.target.value.toUpperCase().slice(0, 2) }))
                  }
                  className="bg-gray-800 border-gray-700 text-white"
                  placeholder="AA"
                  maxLength={2}
                />
              </div>
            </div>

            <Button 
              onClick={() => {
                setShowProfile(false);
                toast.success('Profile updated!');
              }}
              className="w-full bg-cyan-600 hover:bg-cyan-500"
            >
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Chat History Dialog */}
      <Dialog open={showHistory} onOpenChange={setShowHistory}>
        <DialogContent className="bg-gray-900/95 backdrop-blur-lg border-gray-700 text-white max-w-2xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle className="text-white">Chat History</DialogTitle>
            <DialogDescription className="text-gray-400">
              View and manage your conversation history
            </DialogDescription>
          </DialogHeader>

          <div className="flex items-center gap-2 mb-4">
            <Search className="w-4 h-4 text-gray-400" />
            <Input value={historySearch} onChange={e => setHistorySearch(e.target.value)} placeholder="Search chats..." className="bg-gray-800 border-gray-700 text-white placeholder:text-gray-400" />
          </div>

          <div className="flex gap-2 mb-4">
            <Button
              onClick={exportChatHistory}
              variant="outline"
              className="flex-1 border-gray-700 text-white hover:bg-gray-800"
              disabled={chatSessions.length === 0}
            >
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
            <Button
              onClick={clearAllHistory}
              variant="outline"
              className="flex-1 border-red-700 text-red-400 hover:bg-red-900/20"
              disabled={chatSessions.length === 0}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear All
            </Button>
          </div>

          <ScrollArea className="h-[400px] pr-4">
            {chatSessions.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No chat history yet</p>
                <p className="text-sm mt-1">Start a conversation to see it here</p>
              </div>
            ) : filteredSessions.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No matching chats</p>
                <p className="text-sm mt-1">Try a different search term</p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredSessions.map((session) => (
                  <Card
                    key={session.id}
                    className={`p-4 backdrop-blur-lg border cursor-pointer transition-all ${
                      currentSessionId === session.id
                        ? 'bg-cyan-600/20 border-cyan-500'
                        : 'bg-white/5 border-white/10 hover:bg-white/10'
                    }`}
                    onClick={() => loadSession(session.id)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-white truncate mb-1">{session.title}</h4>
                        <div className="flex items-center gap-2 text-xs text-gray-400">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(session.updatedAt).toLocaleDateString()}</span>
                          <span>•</span>
                          <span>{session.messages.length} messages</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e: { stopPropagation: () => void; }) => {
                            e.stopPropagation();
                            renameSession(session.id);
                          }}
                          className="text-cyan-200 hover:bg-white/10 h-8 w-8 p-0"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e: { stopPropagation: () => void; }) => {
                            e.stopPropagation();
                            deleteSession(session.id);
                          }}
                          className="text-red-400 hover:bg-red-900/20 h-8 w-8 p-0"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  );
}
