from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import os
import uvicorn
from app.db.mongodb import check_connection

app = FastAPI(title="SpreadPilot Admin API")

# Define OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

# Define models
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str

# Root endpoint
@app.get("/")
def read_root():
    return {"Hello": "Admin API"}

# Health check endpoint
@app.get("/health")
async def health_check():
    # Check MongoDB connection
    db_connected = await check_connection()
    
    if not db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )
    
    return {"status": "healthy", "database": "connected"}

# Authentication endpoint
@app.post("/api/v1/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # In a real application, you would validate the username and password
    # against the database and generate a JWT token
    # For now, we'll just return a dummy token
    if form_data.username != os.getenv("ADMIN_USERNAME", "admin"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In a real application, you would validate the password hash
    # For now, we'll just return a dummy token
    return {"access_token": "dummy_token", "token_type": "bearer"}

# Protected endpoint example
@app.get("/api/v1/followers")
async def get_followers(token: str = Depends(oauth2_scheme)):
    # In a real application, you would validate the token
    # and retrieve followers from the database
    return {"followers": []}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)