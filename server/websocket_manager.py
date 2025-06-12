from fastapi import WebSocket
from collections import defaultdict
from typing import List, Dict

class WebSocketManager:
    """
    Manages WebSocket connections with topic support.
    Each client receives messages according to the topic to which it has subscribed.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.topic_subscribers: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket):
        """Accepts the connection and adds it to the general list."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Removes the connection from the general list and from all topics."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        for subscribers in self.topic_subscribers.values():
            if websocket in subscribers:
                subscribers.remove(websocket)
      
    async def publish(self, topic: str, message: str):
        """Sends a message to clients subscribed to a given topic."""
        for connection in self.topic_subscribers.get(topic, []):
            await connection.send_json({"topic": topic, "message": message})

    async def broadcast(self, message: str):
        """Sends a message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_json({"topic": "broadcast", "message": message})    
    
    def subscribe(self, websocket: WebSocket, topic: str):
        if websocket not in self.topic_subscribers[topic]:
            self.topic_subscribers[topic].append(websocket)

# on exporte une unique instance
ws_manager = WebSocketManager()
