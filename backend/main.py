from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import init_db
from backend.routers import notas, produtos, painel

app = FastAPI(title="myDANFE API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(notas.router, prefix="/api/notas", tags=["notas"])
app.include_router(produtos.router, prefix="/api/produtos", tags=["produtos"])
app.include_router(painel.router, prefix="/api/painel", tags=["painel"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
