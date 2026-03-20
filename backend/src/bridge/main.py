import asyncio
import json
import logging
import struct
import time
from contextlib import asynccontextmanager

import msgpack
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .recorder import Recorder
from .zmq_client import ZMQClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

recorder = Recorder()
zmq_client = ZMQClient()
active_connections: set[WebSocket] = set()


async def broadcast(message: bytes | str):
    """Broadcast a message to all connected WebSocket clients."""
    disconnected: set[WebSocket] = set()
    for ws in list(active_connections):
        try:
            if isinstance(message, bytes):
                await ws.send_bytes(message)
            else:
                await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        active_connections.discard(ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    zmq_client.set_broadcast_callback(broadcast)
    zmq_client.set_record_callbacks(recorder.record_camera, recorder.record_status)
    await zmq_client.start()
    yield
    await zmq_client.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    logger.info("WebSocket client connected. Total: %d", len(active_connections))

    # Send current recording state on connect so client can re-sync
    await websocket.send_text(
        json.dumps(
            {
                "type": "recording_state",
                "recording": recorder.is_recording,
                "session": recorder.session_name,
            }
        )
    )

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type")

            if msg_type == "command":
                topic = msg.get("topic", "manipulator")
                joint_positions = msg.get("joint_positions", [0.0] * 10)
                await zmq_client.send_command(
                    topic, {"joint_positions": joint_positions}
                )

            elif msg_type == "recording_start":
                if not recorder.is_recording:
                    session = await recorder.start()
                    await broadcast(
                        json.dumps(
                            {
                                "type": "recording_state",
                                "recording": True,
                                "session": session,
                            }
                        )
                    )

            elif msg_type == "recording_stop":
                if recorder.is_recording:
                    session = recorder.session_name
                    # Broadcast stop immediately so the UI updates right away.
                    await broadcast(
                        json.dumps(
                            {
                                "type": "recording_state",
                                "recording": False,
                                "session": session,
                            }
                        )
                    )
                    # Drain queue, close files, and generate preview in background.
                    async def _stop_task(sn=session):
                        sd = await recorder.stop()
                        await recorder.generate_previews(sd)
                        await broadcast(
                            json.dumps(
                                {
                                    "type": "preview_ready",
                                    "session": sn,
                                }
                            )
                        )

                    asyncio.create_task(_stop_task())

            else:
                logger.warning("Unknown WS message type: %s", msg_type)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        active_connections.discard(websocket)
        logger.info("WebSocket client removed. Total: %d", len(active_connections))
