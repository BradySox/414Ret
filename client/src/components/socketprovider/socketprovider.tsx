// Based on https://thenable.io/building-a-use-socket-hook-in-react.
import { WEBSOCKET_URL } from "../../api/backend";
import { ReactChild, createContext, useEffect, useState } from "react";

const INITIAL_RECONNECT_DELAY_MS = 250;
const MAX_RECONNECT_DELAY_MS = 10000;

export const SocketContext = createContext<WebSocket | null>(null);

interface SocketProviderProps {
  children: ReactChild;
}

export const SocketProvider = (props: SocketProviderProps) => {
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    let active = true;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectAttempts = 0;

    const connect = () => {
      if (!active) {
        return;
      }

      socket = new WebSocket(WEBSOCKET_URL);
      setWs(socket);
      socket.addEventListener("open", () => {
        reconnectAttempts = 0;
      });
      socket.addEventListener("close", () => {
        if (!active) {
          return;
        }
        setWs(null);
        const baseDelay = Math.min(
          INITIAL_RECONNECT_DELAY_MS * 2 ** reconnectAttempts,
          MAX_RECONNECT_DELAY_MS
        );
        const jitter = Math.random() * baseDelay * 0.2;
        reconnectAttempts += 1;
        reconnectTimer = setTimeout(connect, baseDelay + jitter);
      });
      socket.addEventListener("error", () => {
        socket?.close();
      });
    };

    connect();

    return () => {
      active = false;
      if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, []);

  return (
    <SocketContext.Provider value={ws}>{props.children}</SocketContext.Provider>
  );
};
