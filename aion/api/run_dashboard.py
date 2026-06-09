"""Lance le dashboard AION v2."""
import uvicorn
from aion.dashboard.server import app

if __name__ == "__main__":
    uvicorn.run(
        "aion.dashboard.server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
