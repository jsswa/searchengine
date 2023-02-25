from fastapi import FastAPI
from app.api.api_router import router as search_router

app = FastAPI()

app.include_router(search_router, prefix='/books')
