import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=int(os.getenv("BACKEND_PORT", 8001)),
        reload=os.getenv("UVICORN_RELOAD", "").lower() in {"1", "true", "yes"}
    )
