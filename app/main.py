from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers import health, ingest, suggestions, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Virtual Assistant - Task Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"])


@app.get("/")
def root():
    return {"ok": True, "service": "task", "version": "0.1.0"}
