import asyncio
from fastapi import WebSocket, Body
from server.websocket_manager import WebSocketManager

ws_manager = WebSocketManager()

async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket entry point.
    Messages received must be in JSON format and contain :
      - topic": to identify the nature of the message (e.g. ‘open_file’)
      - message": the content (e.g. a file path)
    """
    await ws_manager.connect(websocket)
    #ws_manager.subscribe(websocket, "open_file")
    try:
        while True:
            data = await websocket.receive_json()
            topic = data.get("topic", "default")
            message = data.get("message", "")
            action = data.get("action", "")

            # Message sent to customers subscribing to the same topic
            if action == "subscribe" and topic:
                ws_manager.subscribe(websocket, topic)
                print(f"✅ Client subscribed to topic [{topic}]")
                
            elif action == "publish" and topic and message:
                print(f"📩 Message published on topic [{topic}]: {message}")
                await ws_manager.publish(topic, message)

            elif action == "wait_for_permission" and topic:
                # Waiting for a subscriber to arrive
                while len(ws_manager.topic_subscribers.get(topic, [])) == 0:
                    await asyncio.sleep(0.1)
                # await websocket.send_json({"permission": True})
                await websocket.send_json({"topic":topic, "action":"wait_for_permission","message": True})
                
                print(f"✅ Permission granted for topic [{topic}: {action}]")
                


            elif action == "broadcast" and message:
                print(f"📢 Broadcasting message: {message}")
                await ws_manager.broadcast(message)
    except Exception as e:
        print(f"⚠️ Server WebSocket status: {e}")
    finally:
        ws_manager.disconnect(websocket)
