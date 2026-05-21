import React, { useState, useRef } from 'react';
import { Minus, Square, X, Copy } from 'lucide-react';
import { usePyBridgeContext } from '../hooks/usePyBridge';

export function TitleBar() {
  const { isConnected } = usePyBridgeContext();
  const [isMaximized, setIsMaximized] = useState(false);
  const draggingRef = useRef(false);
  const startPosRef = useRef({ x: 0, y: 0 });

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
      
      window.pyBridge?.move_window?.(globalX, globalY);
    };

    const handleMouseUp = () => {
      draggingRef.current = false;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  return (
    <div className="flex items-center justify-between h-10 w-full bg-gray-950 text-gray-400 select-none border-b border-gray-800">
      {/* Drag Handle Area */}
      <div className="flex-1 h-full flex items-center pl-4 font-semibold text-sm text-gray-200 cursor-move" onMouseDown={handleMouseDown}>
        U.L.T.R.O.N Assistant
      </div>

      {/* Window Controls */}
      <div className="flex h-full">
        <button 
          onClick={handleMinimize} 
          className="flex items-center justify-center w-12 h-full hover:bg-gray-800 hover:text-white transition-colors"
        >
          <Minus size={16} />
        </button>
        
        <button 
          onClick={handleMaximize} 
          className="flex items-center justify-center w-12 h-full hover:bg-gray-800 hover:text-white transition-colors"
        >
          {isMaximized ? <Copy size={14} /> : <Square size={14} />}
        </button>
        
        <button 
          onClick={handleClose} 
          className="flex items-center justify-center w-12 h-full hover:bg-red-600 hover:text-white transition-colors"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}