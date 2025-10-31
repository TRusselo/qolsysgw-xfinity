import asyncio
import json
import logging
import ssl
import websockets
from typing import Dict, Optional, Callable

from .events import XfinityEvent


LOGGER = logging.getLogger(__name__)


class XfinitySocket:
    def __init__(self, hostname: str, port: int, token: str,
                 callback: Callable = None,
                 connected_callback: Callable = None,
                 disconnected_callback: Callable = None):
        self._hostname = hostname
        self._port = port
        self._token = token
        self._callback = callback
        self._connected_callback = connected_callback
        self._disconnected_callback = disconnected_callback
        
        self._websocket = None
        self._connected = False
        self._ssl_context = None
        
    async def _connect(self):
        """Establish WebSocket connection to Xfinity box"""
        if self._connected:
            return

        # Initialize SSL context if needed
        if not self._ssl_context:
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE

        uri = f"wss://{self._hostname}:{self._port}/control4"
        
        try:
            self._websocket = await websockets.connect(
                uri,
                ssl=self._ssl_context,
                extra_headers={'Authorization': f'Bearer {self._token}'}
            )
            self._connected = True
            
            if self._connected_callback:
                await self._connected_callback()
                
            LOGGER.info(f"Connected to Xfinity box at {self._hostname}")
            
        except Exception as e:
            LOGGER.error(f"Failed to connect to Xfinity box: {e}")
            self._connected = False
            
            if self._disconnected_callback:
                await self._disconnected_callback()

    async def listen(self):
        """Listen for messages from the Xfinity box"""
        while True:
            try:
                if not self._connected:
                    await self._connect()
                    continue

                message = await self._websocket.recv()
                
                try:
                    event = XfinityEvent.from_json(message)
                    if self._callback:
                        await self._callback(event)
                except Exception as e:
                    LOGGER.error(f"Error processing message: {e}")

            except websockets.exceptions.ConnectionClosed:
                LOGGER.warning("Connection closed, attempting to reconnect...")
                self._connected = False
                if self._disconnected_callback:
                    await self._disconnected_callback()
                await asyncio.sleep(5)  # Wait before reconnecting
                
            except Exception as e:
                LOGGER.error(f"Unexpected error in listen loop: {e}")
                await asyncio.sleep(5)

    async def send(self, message: Dict):
        """Send a message to the Xfinity box"""
        if not self._connected:
            await self._connect()

        try:
            await self._websocket.send(json.dumps(message))
        except Exception as e:
            LOGGER.error(f"Failed to send message: {e}")
            self._connected = False
            if self._disconnected_callback:
                await self._disconnected_callback()

    async def keep_alive(self):
        """Send periodic keep-alive messages"""
        while True:
            if self._connected:
                try:
                    await self.send({"action": "keep_alive"})
                except:  # noqa: E722
                    pass
            await asyncio.sleep(240)  # Keep alive every 4 minutes