export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';
export type StreamingUpdate = {
  type: string;
  provider?: string;
  content?: string;
  chunk?: string;
  message?: string;
  queue?: string[];
  total_providers?: number;
};

class ChatWebSocket {
  private ws: WebSocket | null = null;
  private conversationId: string;
  private onUpdate: (update: StreamingUpdate) => void;
  private onStatusChange: (status: ConnectionStatus) => void;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(
    conversationId: string,
    onUpdate: (update: StreamingUpdate) => void,
    onStatusChange: (status: ConnectionStatus) => void
  ) {
    this.conversationId = conversationId;
    this.onUpdate = onUpdate;
    this.onStatusChange = onStatusChange;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('✓ WebSocket already connected');
      return;
    }

    console.log('🔌 Initiating WebSocket connection...');
    this.onStatusChange('connecting');
    
    // Best practice: Direct connection in development, relative in production
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let wsUrl: string;
    
    if (process.env.NODE_ENV === 'development') {
      // Direct connection to backend in development (bypasses proxy issues)
      wsUrl = `${protocol}//localhost:8000/api/chat/stream/${this.conversationId}`;
    } else {
      // Relative URL in production (same origin)
      wsUrl = `${protocol}//${window.location.host}/api/chat/stream/${this.conversationId}`;
    }
    
    console.log('🌐 Connecting to:', wsUrl);
    
    try {
      this.ws = new WebSocket(wsUrl);
    } catch (error) {
      console.error('✗ Failed to create WebSocket:', error);
      this.onStatusChange('error');
      return;
    }

    this.ws.onopen = () => {
      console.log('✓ WebSocket connected successfully');
      this.onStatusChange('connected');
      this.reconnectAttempts = 0;
      
      // Send a connection initialization message
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        console.log('📤 Sending connection init message');
        this.ws.send(JSON.stringify({
          type: 'connection_init',
          conversation_id: this.conversationId
        }));
      }
    };

    this.ws.onmessage = (event) => {
      console.log('📥 WebSocket message received:', event.data);
      try {
        const update: StreamingUpdate = JSON.parse(event.data);
        this.onUpdate(update);
      } catch (error) {
        console.error('✗ Failed to parse WebSocket message:', error, 'Raw data:', event.data);
      }
    };

    this.ws.onclose = (event) => {
      console.log(`🔌 WebSocket disconnected - Code: ${event.code}, Reason: ${event.reason || 'None'}, Clean: ${event.wasClean}`);
      this.onStatusChange('disconnected');
      
      if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
        console.log('🔄 Scheduling reconnect...');
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('✗ WebSocket error occurred:', error);
      this.onStatusChange('error');
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.onStatusChange('disconnected');
  }

  sendMessage(content: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'user_message',
        content: content.trim(),
      };
      console.log('📤 Sending message:', message);
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('✗ WebSocket is not connected. Current state:', this.getConnectionState());
      this.onStatusChange('error');
      // Attempt to reconnect if we have a valid conversation
      if (this.conversationId && this.reconnectAttempts < this.maxReconnectAttempts) {
        console.log('🔄 Attempting to reconnect before sending message...');
        this.connect();
      }
    }
  }

  private scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000); // Cap at 30 seconds
    
    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
    
    setTimeout(() => {
      if (this.ws?.readyState !== WebSocket.OPEN && this.reconnectAttempts <= this.maxReconnectAttempts) {
        console.log(`Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
        this.connect();
      } else if (this.reconnectAttempts > this.maxReconnectAttempts) {
        console.error('Max reconnection attempts reached. Giving up.');
        this.onStatusChange('error');
      }
    }, delay);
  }

  getConnectionState(): ConnectionStatus {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'error';
    }
  }
}

export default ChatWebSocket;
