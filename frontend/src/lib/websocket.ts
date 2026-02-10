/**
 * Cliente WebSocket para receber progresso do pipeline em tempo real.
 */

function getWsBase(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}`;
  }
  return "ws://localhost:8000";
}

export interface ProgressMessage {
  type: "progress" | "pong";
  project_id?: string;
  step?: string;
  progress?: number;
  message?: string;
  status?: string;
  elapsed_seconds?: number;
  eta_seconds?: number | null;
  timestamp?: number;
}

type ProgressCallback = (message: ProgressMessage) => void;

export class PipelineWebSocket {
  private ws: WebSocket | null = null;
  private projectId: string;
  private callbacks: ProgressCallback[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private disposed = false;

  constructor(projectId: string) {
    this.projectId = projectId;
  }

  connect(): void {
    if (this.disposed) return;

    const url = `${getWsBase()}/ws/${this.projectId}`;
    try {
      this.ws = new WebSocket(url);
    } catch {
      this.scheduleReconnect();
      return;
    }

    const currentWs = this.ws;

    currentWs.onopen = () => {
      if (this.disposed) {
        currentWs.close();
        return;
      }
      this.reconnectAttempts = 0;
      this.pingInterval = setInterval(() => {
        if (currentWs.readyState === WebSocket.OPEN) {
          currentWs.send("ping");
        }
      }, 30000);
    };

    currentWs.onmessage = (event) => {
      if (this.disposed) return;
      try {
        const message: ProgressMessage = JSON.parse(event.data);
        this.callbacks.forEach((cb) => cb(message));
      } catch {
        // Ignorar mensagens inválidas
      }
    };

    currentWs.onclose = () => {
      this.clearPing();
      if (!this.disposed) {
        this.scheduleReconnect();
      }
    };

    currentWs.onerror = () => {
      // onclose fires after onerror
    };
  }

  private clearPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.disposed) return;
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(Math.pow(2, this.reconnectAttempts) * 1000, 30000);
      setTimeout(() => this.connect(), delay);
    }
  }

  onProgress(callback: ProgressCallback): () => void {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter((cb) => cb !== callback);
    };
  }

  disconnect(): void {
    this.disposed = true;
    this.clearPing();
    this.callbacks = [];
    if (this.ws) {
      // Only close if already OPEN — avoid "closed before established" error
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.close();
      } else if (this.ws.readyState === WebSocket.CONNECTING) {
        // Let onopen handle it via the disposed flag
        const pendingWs = this.ws;
        pendingWs.onopen = () => pendingWs.close();
      }
      this.ws = null;
    }
  }
}
