from fastapi import FastAPI
from gateway.app.auth.controller import auth_controller 
app = FastAPI()
app.include_router(auth_controller.router)
@app.get("/")
def read_root():
    return {"message": "DevOps Assistant Agent is running!"}
