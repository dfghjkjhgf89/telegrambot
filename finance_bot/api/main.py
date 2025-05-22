from fastapi import FastAPI

app = FastAPI(
    title="FinanceBot API",
    description="API for FinanceBot WebApp and other integrations.",
    version="0.1.0"
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to FinanceBot API"}

# Placeholder for database connection setup
# async def connect_to_db():
#     pass # Replace with actual database connection logic

# Placeholder for startup and shutdown events
# @app.on_event("startup")
# async def startup_event():
#     await connect_to_db()

# @app.on_event("shutdown")
# async def shutdown_event():
#     pass # Replace with database disconnection logic

# Add more routers and endpoints here as the API grows
# from .routers import debts, transactions # Example for future structure
# app.include_router(debts.router, prefix="/api/v1/debts", tags=["Debts"])
# app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])

if __name__ == "__main__":
    import uvicorn
    # This is for local development.
    # For production, use a proper ASGI server like Gunicorn with Uvicorn workers.
    uvicorn.run(app, host="0.0.0.0", port=8000)
