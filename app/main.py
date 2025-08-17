import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

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

#debug exception handler (turn off if not needed)
#@app.exception_handler(Exception)
#async def _debug_exceptions(request: Request, exc: Exception):
#    # Print the full traceback to the console
#    logging.exception("Unhandled error on %s %s", request.method, request.url.path)
#    return JSONResponse(
#        status_code=500,
#        content={
#            "detail": str(exc),
#            "type": exc.__class__.__name__,
#        },
#    )


app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"])

# Serve the UI at /ui
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")


@app.get("/")
def root():
    return {"ok": True, "service": "task", "version": "0.1.0"}
