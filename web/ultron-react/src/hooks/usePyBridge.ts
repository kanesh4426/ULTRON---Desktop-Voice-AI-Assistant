import { useCallback, useEffect, useState } from 'react';

interface PyBridgeApi {
  move_window?: (x: number, y: number) => void;
  process_message?: (message: string, callback: (response: string) => void) => void;
}

type QWebChannelConstructor = new (
  transport: unknown,
  callback: (channel: { objects: { pyBridge?: PyBridgeApi } }) => void
) => void;

declare global {
  interface Window {
    qt?: {
      webChannelTransport?: unknown;
    };
    QWebChannel?: QWebChannelConstructor;
    pyBridge?: PyBridgeApi;
  }
}

const QWEBCHANNEL_SCRIPT_ID = 'qt-webchannel-script';
const BRIDGE_INIT_RETRY_MS = 250;
const MAX_BRIDGE_INIT_ATTEMPTS = 20;

function ensureQWebChannelLoaded(): Promise<boolean> {
  if (typeof window.QWebChannel === 'function') {
    return Promise.resolve(true);
  }

  const existingScript = document.getElementById(QWEBCHANNEL_SCRIPT_ID) as HTMLScriptElement | null;
  if (existingScript) {
    return new Promise((resolve) => {
      existingScript.addEventListener('load', () => resolve(Boolean(window.QWebChannel)), { once: true });
      existingScript.addEventListener('error', () => resolve(false), { once: true });
    });
  }

  return new Promise((resolve) => {
    const script = document.createElement('script');
    script.id = QWEBCHANNEL_SCRIPT_ID;
    script.src = '/qwebchannel.js';
    script.async = true;
    script.onload = () => resolve(Boolean(window.QWebChannel));
    script.onerror = () => resolve(false);
    document.head.appendChild(script);
  });
}

export function usePyBridge() {
  const [isConnected, setIsConnected] = useState(() => Boolean(window.pyBridge));

  useEffect(() => {
    let cancelled = false;
    let retryTimerId: number | null = null;
    let attempts = 0;

    const initBridge = async () => {
      if (cancelled) {
        return;
      }

      if (window.pyBridge) {
        setIsConnected(true);
        return;
      }

      if (!window.qt?.webChannelTransport) {
        attempts += 1;
        if (attempts < MAX_BRIDGE_INIT_ATTEMPTS) {
          retryTimerId = window.setTimeout(() => {
            void initBridge();
          }, BRIDGE_INIT_RETRY_MS);
        } else {
          setIsConnected(false);
        }
        return;
      }

      const loaded = await ensureQWebChannelLoaded();
      if (!loaded || !window.QWebChannel || cancelled) {
        setIsConnected(false);
        return;
      }

      new window.QWebChannel(window.qt.webChannelTransport, (channel) => {
        if (cancelled) {
          return;
        }

        window.pyBridge = channel.objects.pyBridge;
        setIsConnected(Boolean(window.pyBridge));
      });
    };

    void initBridge();

    return () => {
      cancelled = true;
      if (retryTimerId !== null) {
        window.clearTimeout(retryTimerId);
      }
    };
  }, []);

  const sendMessageToPy = useCallback((message: string, timeoutMs = 5000): Promise<string> => {
    return new Promise((resolve, reject) => {
      const timer = window.setTimeout(
        () => reject(new Error('PyBridge response timeout')),
        timeoutMs
      );

      if (window.pyBridge?.process_message) {
        window.pyBridge.process_message(message, (response: string) => {
          window.clearTimeout(timer);
          resolve(response);
        });
        return;
      }

      window.clearTimeout(timer);
      console.warn('PyBridge is not connected. Returning a browser fallback response.');
      resolve(`[Browser Fallback]: ${message}`);
    });
  }, []);

  return { isConnected, sendMessageToPy };
}
