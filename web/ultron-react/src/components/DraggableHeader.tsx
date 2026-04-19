import React, { useRef } from 'react';
import { toast } from 'sonner';
import { usePyBridge } from '../hooks/usePyBridge';

/**
 * Example Draggable Header Component.
 * Drop this into your UI so you can move the frameless window.
 */
export function DraggableHeader() {
  const { isConnected, sendMessageToPy } = usePyBridge();
  const draggingRef = useRef(false);
  const startPosRef = useRef({ x: 0, y: 0 });

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!isConnected || !window.pyBridge?.move_window) return;
    
    draggingRef.current = true;
    // Store where the user clicked relative to the window itself
    startPosRef.current = { x: e.clientX, y: e.clientY };

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!draggingRef.current) return;
      
      // Determine global desktop coordinates, subtracting the initial local offset
      const globalX = moveEvent.screenX - startPosRef.current.x;
      const globalY = moveEvent.screenY - startPosRef.current.y;
      
      // Move the desktop window
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

  const handleTestBridge = async () => {
    try {
      const response = await sendMessageToPy("Status Check from React!");
      try {
        const parsed = JSON.parse(response);
        toast.success(`Python Says: ${parsed.response || response}`);
      } catch (e) {
        toast.success(`Python Says: ${response}`);
      }
    } catch (error) {
      console.error(error);
      toast.error('Unable to reach the Python bridge.');
    }
  };

  return (
    <header className="flex justify-between items-center bg-gray-900/90 text-white p-4 border-b border-gray-700 select-none backdrop-blur-lg">
      <div className="flex-1 cursor-move" onMouseDown={handleMouseDown}>
        <h1 className="text-xl font-bold tracking-wider text-cyan-400">ULTRON</h1>
      </div>
      <div className="flex items-center gap-4">
        <button
          onMouseDown={(e) => e.stopPropagation()}
          onClick={handleTestBridge}
          className="bg-cyan-600 hover:bg-cyan-500 px-3 py-1 rounded text-sm transition-colors"
        >
          Test Connection
        </button>
      </div>
    </header>
  );
}
