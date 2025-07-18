/**
 * WebSocket service for research task progress streaming
 */

import { ResearchProgressUpdate } from './api';

export type ResearchProgressCallback = (update: ResearchProgressUpdate) => void;
export type ConnectionStatusCallback = (status: 'disconnected' | 'connecting' | 'connected' | 'error') => void;

class ResearchWebSocket {
  private ws: WebSocket | null = null;
  private taskId: string;
  private onProgress: ResearchProgressCallback;
  private onConnectionStatus: ConnectionStatusCallback;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(
    taskId: string,
    onProgress: ResearchProgressCallback,
    onConnectionStatus: ConnectionStatusCallback
  ) {
    this.taskId = taskId;
    this.onProgress = onProgress;
    this.onConnectionStatus = onConnectionStatus;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.onConnectionStatus('connecting');
    
    const wsUrl = process.env.NODE_ENV === 'development' 
      ? `ws://localhost:8000/api/research/stream/${this.taskId}`
      : `ws://${window.location.host}/api/research/stream/${this.taskId}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('Research WebSocket connected for task:', this.taskId);
      this.onConnectionStatus('connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const update = JSON.parse(event.data) as ResearchProgressUpdate;
        this.onProgress(update);
      } catch (error) {
        console.error('Failed to parse research WebSocket message:', error);
      }
    };

    this.ws.onclose = (event) => {
      console.log('Research WebSocket disconnected:', event.code, event.reason);
      this.onConnectionStatus('disconnected');
      
      // Attempt to reconnect if not manually closed
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect();
        }, this.reconnectDelay * this.reconnectAttempts);
      }
    };

    this.ws.onerror = (error) => {
      console.error('Research WebSocket error:', error);
      this.onConnectionStatus('error');
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting');
      this.ws = null;
    }
  }

  cancelTask(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'cancel_task' }));
    }
  }

  sendKeepalive(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'ping' }));
    }
  }
}

export default ResearchWebSocket;
