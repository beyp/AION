"""Point d entree pour lancer le serveur AION API."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "aion.api.server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
