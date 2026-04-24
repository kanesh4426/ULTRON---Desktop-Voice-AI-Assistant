import React, { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Input } from './ui/input';
import { Mic, MicOff, Send, Volume2 } from 'lucide-react';
import { toast } from 'sonner';
import { createId } from '../lib/app-utils';
import { usePyBridge } from '../hooks/usePyBridge';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

export function ChatInterface() {
  const { isConnected, sendMessageToPy } = usePyBridge();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: "Hello! I'm your AI assistant. You can type or use voice to talk with me. How can I help you today?",
      sender: 'ai',
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [recognition, setRecognition] = useState<any>(null);
  const [speechSynthesis, setSpeechSynthesis] = useState<SpeechSynthesis | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initialize speech recognition
    let recognitionInstance: any = null;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      recognitionInstance = new SpeechRecognition();
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = 'en-US';

      recognitionInstance.onresult = (event:any) => {
        const transcript = event.results[0][0].transcript;
        setInputText(transcript);
        setIsListening(false);
      };

      recognitionInstance.onerror = () => {
        setIsListening(false);
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
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    const textToSend = inputText.trim();
    if (!textToSend) return;

    const userMessage: Message = {
      id: createId(),
      text: textToSend,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');

    if (!isConnected) {
      toast.error('Not connected to the Python backend.');
      return;
    }

    try {
      const response = await sendMessageToPy(textToSend);
      let responseText = response;
      try {
        const parsed = JSON.parse(response);
        responseText = parsed.response || response;
      } catch (e) {
        // Not JSON
      }

      const aiResponse: Message = {
        id: createId(),
        text: responseText,
        sender: 'ai',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiResponse]);
    } catch (error) {
      console.error(error);
      toast.error('Unable to reach the Python backend.');
    }
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
      } catch (err) {
        console.error('Speech recognition start error:', err);
        toast.error('Microphone access denied or unavailable.');
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
    utterance.rate = 0.8;
    utterance.pitch = 1;
    
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <Card className={`max-w-[70%] p-3 ${
              message.sender === 'user' 
                ? 'bg-primary text-primary-foreground' 
                : 'bg-muted'
            }`}>
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm">{message.text}</p>
                {message.sender === 'ai' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="shrink-0 h-6 w-6 p-0"
                    onClick={() => handleSpeak(message.text)}
                  >
                    <Volume2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
              <p className="text-xs opacity-70 mt-1">
                {message.timestamp.toLocaleTimeString()}
              </p>
            </Card>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form 
        onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} 
        className="p-4 border-t bg-background"
      >
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Input
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type your message or use voice input..."
              className="pr-12"
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className={`absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8 p-0 ${
                isListening ? 'text-destructive' : ''
              }`}
              onClick={handleVoiceInput}
            >
              {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            </Button>
          </div>
          <Button type="submit" disabled={!inputText.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
        
        {isListening && (
          <div className="mt-2 text-center">
            <p className="text-sm text-muted-foreground animate-pulse">
              Listening... Speak now
            </p>
          </div>
        )}
        
        {isSpeaking && (
          <div className="mt-2 text-center">
            <p className="text-sm text-muted-foreground animate-pulse">
              Speaking...
            </p>
          </div>
        )}
      </form>
    </div>
  );
}
