class WebSocketService {
  constructor() {
    this.socket = null;
    this.listeners = new Set();
  }

  connect(pipelineId) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return;
    }

    this.socket = new WebSocket(
      `ws://localhost:8000/ws/telemetry?pipelineId=${pipelineId}`
    );

    this.socket.onopen = () => {
      console.log(`WebSocket connected for pipeline ${pipelineId}`);
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Notify all listeners
        this.listeners.forEach((listener) => {
          listener(data);
        });
      } catch (err) {
        console.error("Error parsing message:", err, "Raw data:", event.data);
      }
    };

    this.socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    this.socket.onclose = (event) => {
      console.log(`Connection closed: ${event.code} - ${event.reason}`);
    };
  }

  disconnect() {
    if (this.socket) {
      this.socket.close(1000, "Component unmounted");
      this.socket = null;
    }
  }

  addListener(callback) {
    // Add the callback to the listeners
    this.listeners.add(callback);

    // Return a function to remove this callback
    return () => {
      this.listeners.delete(callback);
    };
  }

  send(message) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }
}

export const webSocketService = new WebSocketService();
