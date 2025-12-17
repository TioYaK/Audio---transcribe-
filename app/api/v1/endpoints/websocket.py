
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import os
from app.core.config import logger
from app.core.websocket_manager import ws_manager

router = APIRouter()

@router.websocket("/ws/tasks/{task_id}")
async def websocket_task_updates(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint para updates em tempo real de uma task específica.
    Cliente recebe atualizações de status e progresso automaticamente.
    """
    await ws_manager.connect(websocket, task_id)
    logger.info(f"WebSocket conectado para task {task_id}")
    
    try:
        # Enviar mensagem inicial de conexão
        await ws_manager.send_personal_message({
            "type": "connected",
            "task_id": task_id,
            "message": "Conectado ao servidor de updates"
        }, websocket)
        
        # Manter conexão aberta e aguardar mensagens (heartbeat)
        while True:
            try:
                # Aguardar mensagem do cliente (ping/pong para manter vivo)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Responder a ping
                if data == "ping":
                    await ws_manager.send_personal_message({
                        "type": "pong"
                    }, websocket)
            except asyncio.TimeoutError:
                # Timeout normal - enviar ping para verificar conexão
                await ws_manager.send_personal_message({
                    "type": "ping"
                }, websocket)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket desconectado para task {task_id}")
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Erro no WebSocket para task {task_id}: {e}")
        ws_manager.disconnect(websocket)
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected for logs")
    log_file = "/app/data/app.log"
    
    try:
        # Initial read - send last 20 lines
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                 lines = f.readlines()
                 for line in lines[-20:]:
                     await websocket.send_text(line)
                     
            # Tail logic
            f = open(log_file, 'r', encoding='utf-8', errors='ignore')
            f.seek(0, 2) # Go to end
            
            while True:
                line = f.readline()
                if line:
                    await websocket.send_text(line)
                else:
                    await asyncio.sleep(0.5)
        else:
             await websocket.send_text("Log file not found.")
             await websocket.close()
             
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try: await websocket.close()
        except: pass
