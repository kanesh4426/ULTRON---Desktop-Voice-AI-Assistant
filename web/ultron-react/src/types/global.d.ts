export {};

interface PyBridgeApi {
  move_window: (x: number, y: number) => void;
  minimize_window: () => void;
  maximize_window: () => void;
  close_window: () => void;
  process_message: (message: string, callback: (response: string) => void) => void;
  login: (email: string, pass: string, callback: (response: string) => void) => void;
  signup: (name: string, email: string, pass: string, callback: (response: string) => void) => void;
}

declare global {
  interface Window {
    pyBridge?: PyBridgeApi;
  }
}