from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import connect, close
from .routes import customers, executive, forecast, fraud, merchants, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()
    yield
    await close()


app = FastAPI(
    title="Payment Analytics API",
    description="Enterprise payment analytics platform — transactions, merchants, fraud & executive insights",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router, prefix="/api")
app.include_router(merchants.router, prefix="/api")
app.include_router(fraud.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(executive.router, prefix="/api")
app.include_router(forecast.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
