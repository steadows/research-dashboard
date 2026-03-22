import { useEffect, useRef, useCallback, useState } from "react";
import type { Fetcher, SWRConfiguration } from "swr";

// ─── Base URL Configuration ─────────────────────────────────────────────────

/** HTTP API uses same-origin paths (proxied via next.config rewrites) */
const API_BASE = "/api";

/** WebSocket URL from env — direct connection in dev, reverse proxy in prod */
const WS_BASE =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_WS_URL ??
      `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`
    : "";

// ─── SWR Fetcher ────────────────────────────────────────────────────────────

/**
 * Default SWR fetcher — appends API_BASE and parses JSON.
 * Throws on non-2xx responses with the response body as context.
 */
export const apiFetcher: Fetcher<unknown, string> = async (path: string) => {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url);

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    const error = new Error(`API error ${res.status}: ${body}`);
    (error as ApiError).status = res.status;
    throw error;
  }

  return res.json();
};

interface ApiError extends Error {
  status: number;
}

/** Default SWR config for all hooks */
export const defaultSWRConfig: SWRConfiguration = {
  fetcher: apiFetcher as Fetcher,
  revalidateOnFocus: false,
  dedupingInterval: 5000,
};

// ─── Mutation Helpers ───────────────────────────────────────────────────────

interface MutationOptions {
  method?: "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
}

/**
 * Generic mutation helper for POST/PUT/PATCH/DELETE requests.
 * Returns parsed JSON response.
 */
export async function apiMutate<T = unknown>(
  path: string,
  options: MutationOptions = {}
): Promise<T> {
  const { method = "POST", body } = options;
  const url = `${API_BASE}${path}`;

  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => "");
    throw new Error(`API ${method} ${path} failed (${res.status}): ${errorBody}`);
  }

  return res.json();
}

// ─── WebSocket Hook ─────────────────────────────────────────────────────────

export type WebSocketStatus = "connecting" | "open" | "closed" | "error";

interface UseWebSocketOptions {
  /** WebSocket path (appended to WS_BASE) */
  path: string;
  /** Auto-reconnect on close — defaults to true */
  reconnect?: boolean;
  /** Reconnect delay in ms — defaults to 3000 */
  reconnectDelay?: number;
  /** Max reconnect attempts — defaults to 5 */
  maxRetries?: number;
  /** Callback for incoming messages */
  onMessage?: (data: unknown) => void;
}

interface UseWebSocketReturn {
  status: WebSocketStatus;
  send: (data: unknown) => void;
  close: () => void;
  lastMessage: unknown;
}

/**
 * React hook for WebSocket connections to the FastAPI backend.
 * Handles auto-reconnect, JSON parsing, and cleanup.
 */
export function useWebSocket({
  path,
  reconnect = true,
  reconnectDelay = 3000,
  maxRetries = 5,
  onMessage,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [status, setStatus] = useState<WebSocketStatus>("connecting");
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const mountedRef = useRef(true);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    const url = `${WS_BASE}${path}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    setStatus("connecting");

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setStatus("open");
      retriesRef.current = 0;
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);
        onMessageRef.current?.(data);
      } catch {
        setLastMessage(event.data);
        onMessageRef.current?.(event.data);
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setStatus("closed");

      if (reconnect && retriesRef.current < maxRetries) {
        retriesRef.current += 1;
        const delay = reconnectDelay * Math.pow(2, retriesRef.current - 1);
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      if (!mountedRef.current) return;
      setStatus("error");
    };
  }, [path, reconnect, reconnectDelay, maxRetries]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === "string" ? data : JSON.stringify(data));
    }
  }, []);

  const close = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    wsRef.current?.close();
  }, []);

  return { status, send, close, lastMessage };
}
