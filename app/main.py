from fastapi import FastAPI
from app.config import db
from app.auth.auth_routes import router as auth_router
from app.url.url_routes import router as url_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

app = FastAPI()

# @app.on_event("startup")
# async def startup():
#     await db.connect()
    
# @app.on_event("shutdown")
# async def shutdown():
#     await db.disconnect()

@app.get("/")
async def root():
    return {"message": "Welcome to the URL Shortener API"}

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="URL Shortener API",
        version="1.0.0",
        description="API for registering, logging in, and shortening URLs",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", [{"BearerAuth": []}])
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


app.include_router(auth_router, prefix="/auth")
app.include_router(url_router, tags=["URL Shortener"])
