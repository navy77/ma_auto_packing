from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from router import status


app = FastAPI()

##########################################################################################################
# allow middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# status api 
app.include_router(status.router,prefix="/status",tags=["status_current"])

##########################################################################################################


