from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.routes.toolRoutes import tool_router
from server.routes.workflowRoutes import workflow_router
from server.sockets import websocket_endpoint
from src import getRootPath

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


# # Current directory of the server.py file
# current_dir = os.path.dirname(os.path.abspath(__file__))

# # Directory containing the static files ==> /images and table tool reactjs app (/table_with_react)
# static_dir = os.path.join(current_dir, "static")

# # Mount the static files directory and set follow_symlinks to True to authorize access to the images directory
# static_images_path = os.path.join(static_dir, "images")
# app.mount("/images", StaticFiles(directory=static_images_path, follow_symlink=True), name="images")

# # Mount the Table Tool ReactJS  App
# table_tool_reactjs_build_dir = os.path.join(static_dir, "table_with_react")
# app.mount("/react", StaticFiles(directory=table_tool_reactjs_build_dir), name="react")

# # ------------------------------------------------------------------
# # catch-all Route for  Table Tool ReactJS 
# # ------------------------------------------------------------------
# @app.get("/react", response_class=HTMLResponse)
# async def serve_react_app():
#     """catch-all Route for  Table Tool ReactJS """
#     index_path = os.path.join(table_tool_reactjs_build_dir, "index.html")
#     try:
#         with open(index_path, "r", encoding="utf-8") as f:
#             html_content = f.read()
#     except Exception as e:
#         return HTMLResponse(content=f"Error while reading index.html file : {e}", status_code=500)
#     return HTMLResponse(content=html_content, status_code=200)


@app.get("/")
def read_root():
    """ HTTP Endpoint to check that FastAPI is working properly."""
    return {"message": "FastAPI WebSocket is running!"}

@app.get("/projectRootPath")
def getProjectPath():
    """HTTP Endpoint to get the root path of the project."""
    return getRootPath()













