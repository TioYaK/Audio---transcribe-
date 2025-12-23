"""
Endpoint para retornar IP publico do servidor
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
import os
import json
from datetime import datetime

router = APIRouter()

@router.get("/public-ip", response_class=PlainTextResponse)
async def get_public_ip_text():
    """Retorna apenas o IP em texto puro"""
    try:
        ip_file = "/app/static/current_ip.txt"
        if os.path.exists(ip_file):
            with open(ip_file, "r") as f:
                return f.read().strip()
        return "IP_NOT_AVAILABLE"
    except:
        return "ERROR"

@router.get("/public-ip/json")
async def get_public_ip_json():
    """Retorna IP com informacoes adicionais em JSON"""
    try:
        json_file = "/app/static/ip_updated.json"
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                data = json.load(f)
                return JSONResponse(content=data)
        
        # Fallback para arquivo de texto
        ip_file = "/app/static/current_ip.txt"
        if os.path.exists(ip_file):
            with open(ip_file, "r") as f:
                return JSONResponse(content={
                    "ip": f.read().strip(),
                    "updated_at": None,
                    "server": "Mirror.ia"
                })
        
        return JSONResponse(content={"error": "IP not available"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
