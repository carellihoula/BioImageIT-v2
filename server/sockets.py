from quart import websocket, Blueprint
import asyncio
import json
import logging

# Configure a logger for this module
logger = logging.getLogger(__name__)

sockets_bp = Blueprint("sockets", __name__)

# Manage multiple connected clients
connected_clients = set()

@sockets_bp.websocket('/ws')
async def ws():
    while True:
        msg = await websocket.receive()
        # await websocket.send(f"Echo: ")
        print(f"message : {msg}")