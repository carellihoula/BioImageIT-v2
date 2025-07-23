from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from server.routes.toolRoutes import tool_router
from server.routes.workflowRoutes import workflow_router
from server.sockets import websocket_endpoint
from src import getRootPath
from pathlib import Path

# "http://localhost:5174",
# "http://localhost:5173",
# "http://localhost:3000",

app = FastAPI()
test_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=test_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(tool_router)
app.include_router(workflow_router)
@app.websocket("/ws")(websocket_endpoint)


@app.get("/")
def read_root():
    """ HTTP Endpoint to check that FastAPI is working properly."""
    return {"message": "FastAPI WebSocket is running!"}

@app.get("/projectRootPath")
def getProjectPath():
    """HTTP Endpoint to get the root path of the project."""
    return getRootPath()

# # Current directory of the server.py file
current_dir = Path(__file__).resolve().parent

# Directory containing the static files ==> /images and reactjs app
static_dir = current_dir / "static"

# Mount the static files directory and set follow_symlinks to True to authorize access to the images directory
static_images_path = static_dir / "images"
app.mount("/images", StaticFiles(directory=static_images_path, follow_symlink=True), name="images")


"""currently unusable, as pywebview internally uses the bottle.py HTTP server to serve static files."""
# Mount the ReactJS  App
# reactjs_build_dir = static_dir / "react_build"
# app.mount("/react", StaticFiles(directory=reactjs_build_dir), name="react")

# ------------------------------------------------------------------
# catch-all Route for ReactJS 
# ------------------------------------------------------------------
# @app.get("/react", response_class=HTMLResponse)
# async def serve_react_app():
#     """catch-all Route for  Table Tool ReactJS """
#     index_path = reactjs_build_dir / "index.html"
#     try:
#         with open(index_path, "r", encoding="utf-8") as f:
#             html_content = f.read()
#     except Exception as e:
#         return HTMLResponse(content=f"Error while reading index.html file : {e}", status_code=500)
#     return HTMLResponse(content=html_content, status_code=200)













