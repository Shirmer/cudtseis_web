import os
import uvicorn


def bool_env(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("BACKEND_PORT", 8001)),
        reload=bool_env("UVICORN_RELOAD"),
    )
