
from fastapi import APIRouter
from app.api.v1.endpoints import auth, tasks, admin, websocket, users

router = APIRouter()

router.include_router(auth.router, tags=["auth"])
router.include_router(tasks.router, prefix="/api", tags=["tasks"])
router.include_router(admin.router, prefix="/api", tags=["admin"])
router.include_router(users.router, prefix="/api", tags=["users"])
router.include_router(websocket.router, tags=["websocket"])
