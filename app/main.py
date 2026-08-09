from fastapi import FastAPI

from app.db import Base, engine
from app.orders import router as orders_router

app = FastAPI(title="orders-api")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(orders_router)
