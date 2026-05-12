import os
import uvicorn

from app.settings import settings


def bool_env(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("BACKEND_HOST", settings.backend_host),
        port=int(os.getenv("BACKEND_PORT", settings.backend_port)),
        reload=bool_env("UVICORN_RELOAD"),
    )
