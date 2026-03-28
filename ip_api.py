from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import re
import uvicorn
from typing import Dict, List
from datetime import datetime

app = FastAPI(title="IP Address API", version="1.0.0")

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# In-memory IP store
# username -> list of IP records
# -----------------------------
IP_STORE: Dict[str, List[Dict[str, str]]] = {}

# -----------------------------
# Username validator
# Accepts SB3, SB4, SB5 ... SBn
# -----------------------------
USERNAME_PATTERN = re.compile(r"^SB[3-9]\d*$")

def is_valid_username(username: str) -> bool:
    return bool(USERNAME_PATTERN.match(username))

# -----------------------------
# Models
# -----------------------------
class IPRequest(BaseModel):
    ip_address: str = Field(..., min_length=7, description="IPv4 or IPv6 address")

class IPRecord(BaseModel):
    ip_address: str
    timestamp: str

class IPResponse(BaseModel):
    status: str
    username: str
    message: str
    ip_address: str
    timestamp: str

# -----------------------------
# Helpers
# -----------------------------
def store_ip(username: str, ip_address: str, timestamp: str):
    IP_STORE.setdefault(username, []).append({
        "ip_address": ip_address,
        "timestamp": timestamp
    })

# -----------------------------
# Root
# -----------------------------
@app.get("/")
async def root():
    return {
        "name": "IP Address API",
        "version": "1.0.0",
        "endpoints": [
            "POST /api/ip_address/save/{username}/",
            "GET  /api/ip_address/save/{username}/",
        ]
    }

# -----------------------------
# POST — save IP for username
# -----------------------------
@app.post("/api/ip_address/save/{username}/", response_model=IPResponse)
async def save_ip(username: str, payload: IPRequest):
    if not is_valid_username(username):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid username '{username}'. Must match pattern SB3, SB4, ... SBn."
        )

    timestamp = datetime.utcnow().isoformat()
    store_ip(username, payload.ip_address, timestamp)

    return IPResponse(
        status="success",
        username=username,
        message=f"IP address saved for {username}",
        ip_address=payload.ip_address,
        timestamp=timestamp
    )

# -----------------------------
# GET — fetch IPs by username
# -----------------------------
@app.get("/api/ip_address/save/{username}/")
async def get_ip(
    username: str,
    limit: int = Query(20, ge=1, le=100)
):
    if not is_valid_username(username):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid username '{username}'. Must match pattern SB3, SB4, ... SBn."
        )

    records = IP_STORE.get(username, [])[-limit:]

    latest = records[-1] if records else None

    return {
        "data": {
            "username": username,
            "ip_address": latest["ip_address"] if latest else None,
        },
        "count": len(records)
    }

# -----------------------------
# Health
# -----------------------------
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "users": len(IP_STORE),
        "total_records": sum(len(v) for v in IP_STORE.values())
    }

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("ip_api:app", host="0.0.0.0", port=port)
