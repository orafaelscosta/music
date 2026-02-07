/**
 * Cliente WebSocket para receber progresso do pipeline em tempo real.
 */

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export interface ProgressMessage {
  type: "progress" | "pong";
  project_id?: string;
  step?: string;
  progress?: number;
  message?: string;
  status?: string;
}

type ProgressCallback = (message: ProgressMessage) => void;

export class PipelineWebSocket {
  private ws: WebSocket | null = null;
  private projectId: string;
  private callbacks: ProgressCallback[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private pingInterval: ReturnType<typeof setInterval> | null = null;

  constructor(projectId: string) {
    this.projectId = projectId;
  }

  connect(): void {
    const url = `${WS_BASE}/ws/${this.projectId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      // Enviar ping a cada 30s para manter conexão viva
      this.pingInterval = setInterval(() => {
        this.ws?.send("ping");
      }, 30000);
    };

    this.ws.onmessage = (event) => {
      try {
        const message: ProgressMessage = JSON.parse(event.data);
        this.callbacks.forEach((cb) => cb(message));
      } catch {
        // Ignorar mensagens inválidas
      }
    };

    this.ws.onclose = () => {
      if (this.pingInterval) clearInterval(this.pingInterval);
      // Tentar reconectar
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = Math.pow(2, this.reconnectAttempts) * 1000;
        setTimeout(() => this.connect(), delay);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  onProgress(callback: ProgressCallback): () => void {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter((cb) => cb !== callback);
    };
  }

  disconnect(): void {
    if (this.pingInterval) clearInterval(this.pingInterval);
    this.maxReconnectAttempts = 0; // Prevent reconnection
    this.ws?.close();
    this.ws = null;
    this.callbacks = [];
  }
}
