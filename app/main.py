import os
import uvicorn
from fastapi import FastAPI
from app.api.api_router import router as search_router

app = FastAPI()

app.include_router(search_router, prefix='/books')

port = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
