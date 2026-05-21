import { useCallback, useEffect, useState, createContext, useContext, ReactNode, useRef, createElement } from 'react';
 
export interface PyBridgeApi {
  move_window?: (x: number, y: number) => void;
  minimize_window?: () => void;
  maximize_window?: () => void;
  close_window?: () => void;
  process_message?: (reqId: string, message: string) => void;
  login?: (email: string, password: string) => void;
  signup?: (name: string, email: string, password: string) => void;
  messageReady?: {
    connect: (callback: (reqId: string, response: string) => void) => void;
    disconnect: (callback: (reqId: string, response: string) => void) => void;
  };
  loginReady?: {
    connect: (cb: (response: string) => void) => void;
    disconnect: (cb: (response: string) => void) => void;
  };
  signupReady?: {
    connect: (cb: (response: string) => void) => void;
    disconnect: (cb: (response: string) => void) => void;
  };
}
 
type QWebChannelConstructor = new (
  transport: unknown,
  callback: (channel: { objects: { pyBridge?: PyBridgeApi } }) => void
) => void;
 
declare global {
  interface Window {
    qt?: { webChannelTransport?: unknown };
    QWebChannel?: QWebChannelConstructor;
    pyBridge?: PyBridgeApi;
  }
}
 
const QWEBCHANNEL_SCRIPT_ID = 'qt-webchannel-script';
const BRIDGE_INIT_RETRY_MS = 250;
const MAX_BRIDGE_INIT_ATTEMPTS = 20;
 
function ensureQWebChannelLoaded(): Promise<boolean> {
  if (typeof window.QWebChannel === 'function') return Promise.resolve(true);
 
  const existingScript = document.getElementById(QWEBCHANNEL_SCRIPT_ID) as HTMLScriptElement | null;
  if (existingScript) {
    return new Promise((resolve) => {
      if (typeof window.QWebChannel === 'function') {
        resolve(true);
        return;
      }
      existingScript.addEventListener('load', () => resolve(Boolean(window.QWebChannel)), { once: true });
      existingScript.addEventListener('error', () => resolve(false), { once: true });
    });
  }
 
  return new Promise((resolve) => {
    const script = document.createElement('script');
    script.id = QWEBCHANNEL_SCRIPT_ID;
    script.src = new URL('qwebchannel.js', window.location.href).href;
    script.async = true;
    script.onload = () => resolve(Boolean(window.QWebChannel));
    script.onerror = () => resolve(false);
    document.head.appendChild(script);
  });
}
 
interface PyBridgeContextType {
  isConnected: boolean;
  sendMessageToPy: (message: string, timeoutMs?: number) => Promise<string>;
}
 
const PyBridgeContext = createContext<PyBridgeContextType>({
  isConnected: false,
  sendMessageToPy: async (message: string) => `[Browser Fallback]: ${message}`,
});
 
export const usePyBridgeContext = () => useContext(PyBridgeContext);
 
export function PyBridgeProvider({ children }: { children: ReactNode }) {
  const [isConnected, setIsConnected] = useState(() => Boolean(window.pyBridge));
  const pendingRequests = useRef<Map<string, { resolve: (res: string) => void, reject: (err: Error) => void, timer: number }>>(new Map());
 
  useEffect(() => {
    let cancelled = false;
    let retryTimerId: number | null = null;
    let attempts = 0;
 
    const handleMessageReady = (reqId: string, response: string) => {
      const pending = pendingRequests.current.get(reqId);
      if (pending) {
        window.clearTimeout(pending.timer);
        pending.resolve(response);
        pendingRequests.current.delete(reqId);
      }
    };
 
    const initBridge = async () => {
      if (cancelled) return;
      if (window.pyBridge) {
        setIsConnected(true);
        window.pyBridge.messageReady?.connect(handleMessageReady);
        return;
      }
 
      if (!window.qt?.webChannelTransport) {
        attempts += 1;
        if (attempts < MAX_BRIDGE_INIT_ATTEMPTS) {
          retryTimerId = window.setTimeout(() => { void initBridge(); }, BRIDGE_INIT_RETRY_MS);
        } else {
          setIsConnected(false);
        }
        return;
      }
 
      const loaded = await ensureQWebChannelLoaded();
      if (!loaded || !window.QWebChannel || cancelled) { setIsConnected(false); return; }
 
      new window.QWebChannel(window.qt.webChannelTransport, (channel) => {
        if (cancelled) return;
        window.pyBridge = channel.objects.pyBridge;
        setIsConnected(Boolean(window.pyBridge));
        window.pyBridge?.messageReady?.connect(handleMessageReady);
      });
    };
 
    void initBridge();
    return () => {
      cancelled = true;
      if (retryTimerId !== null) window.clearTimeout(retryTimerId);
      window.pyBridge?.messageReady?.disconnect?.(handleMessageReady);
    };
  }, []);
 
  const sendMessageToPy = useCallback((message: string, timeoutMs = 30000): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reqId = Math.random().toString(36).substring(2, 15);
      const timer = window.setTimeout(() => {
        pendingRequests.current.delete(reqId);
        reject(new Error('PyBridge response timeout'));
      }, timeoutMs);
 
      if (window.pyBridge?.process_message) {
        pendingRequests.current.set(reqId, { resolve, reject, timer });
        window.pyBridge.process_message(reqId, message);
        return;
      }
 
      window.clearTimeout(timer);
      console.warn('PyBridge not connected. Returning browser fallback.');
      resolve(`[Browser Fallback]: ${message}`);
    });
  }, []);
 
  return createElement(
    PyBridgeContext.Provider,
    { value: { isConnected, sendMessageToPy } },
    children
  );
}
 