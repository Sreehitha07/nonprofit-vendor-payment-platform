from fastapi import FastAPI

app = FastAPI(
    title="Nonprofit Vendor Payment and Transparency Platform",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "Nonprofit Vendor Payment Platform API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }