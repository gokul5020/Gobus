import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { io } from 'socket.io-client';
import { useAuth } from './AuthContext';

const SocketContext = createContext(null);

export function SocketProvider({ children }) {
  const { user } = useAuth();
  const socketRef = useRef(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const socket = io('http://localhost:5000', { transports: ['websocket'] });
    socketRef.current = socket;

    socket.on('connect', () => {
      setConnected(true);
      if (user) {
        if (user.role === 'passenger') {
          socket.emit('join-passenger', user.id);
        } else if (user.role === 'depot' || user.role === 'admin') {
          socket.emit('join-depot');
        }
      }
    });

    socket.on('disconnect', () => setConnected(false));

    return () => socket.disconnect();
  }, [user]);

  return (
    <SocketContext.Provider value={{ socket: socketRef.current, connected }}>
      {children}
    </SocketContext.Provider>
  );
}

export const useSocket = () => useContext(SocketContext);
