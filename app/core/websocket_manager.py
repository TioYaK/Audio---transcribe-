"""
WebSocket Connection Manager for Real-time Task Updates
Manages WebSocket connections and broadcasts task status/progress updates
"""
from fastapi import WebSocket
from typing import Dict, Set
import asyncio
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gerencia conexões WebSocket para updates em tempo real"""
    
    def __init__(self):
        # task_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> task_id (reverse mapping for cleanup)
        self.connection_tasks: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """Aceita nova conexão WebSocket e a associa a uma task"""
        await websocket.accept()
        
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        
        self.active_connections[task_id].add(websocket)
        self.connection_tasks[websocket] = task_id
        
        logger.info(f"WebSocket conectado para task {task_id}. Total: {len(self.active_connections[task_id])}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove conexão WebSocket"""
        if websocket in self.connection_tasks:
            task_id = self.connection_tasks[websocket]
            
            if task_id in self.active_connections:
                self.active_connections[task_id].discard(websocket)
                
                # Limpar set vazio
                if not self.active_connections[task_id]:
                    del self.active_connections[task_id]
            
            del self.connection_tasks[websocket]
            logger.info(f"WebSocket desconectado da task {task_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Envia mensagem para uma conexão específica"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem pessoal: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_task(self, task_id: str, message: dict):
        """Envia mensagem para todos os clientes conectados a uma task"""
        if task_id not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[task_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Erro ao enviar broadcast para task {task_id}: {e}")
                disconnected.append(connection)
        
        # Limpar conexões mortas
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_status_update(self, task_id: str, status: str, progress: int = None, error: str = None):
        """Envia update de status para todos os clientes de uma task"""
        message = {
            "type": "status_update",
            "task_id": task_id,
            "status": status,
        }
        
        if progress is not None:
            message["progress"] = progress
        
        if error:
            message["error"] = error
        
        await self.broadcast_to_task(task_id, message)
    
    async def send_progress_update(self, task_id: str, progress: int):
        """Envia update de progresso"""
        message = {
            "type": "progress_update",
            "task_id": task_id,
            "progress": progress
        }
        
        await self.broadcast_to_task(task_id, message)
    
    async def send_completion(self, task_id: str, result: dict):
        """Envia notificação de conclusão com resultado"""
        message = {
            "type": "completion",
            "task_id": task_id,
            "result": result
        }
        
        await self.broadcast_to_task(task_id, message)


# Instância global
ws_manager = ConnectionManager()
