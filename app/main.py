from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import Base, engine
from app.orders import router as orders_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="orders-api", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(orders_router)
