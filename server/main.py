

from quart import Quart, jsonify
from .routes.workflowRoutes import workflow_bp
from .routes.toolRoutes import tool_bp
from quart_cors import cors

    
app = Quart(__name__, static_folder=None)
app.config['PROVIDE_AUTOMATIC_OPTIONS'] = True
app = cors(app, allow_origin=["http://localhost:5173"])

app.register_blueprint(workflow_bp)
app.register_blueprint(tool_bp)

@app.route('/health') 
async def health():
    print("--- server/main.py: Route '/health' called ---")
    return jsonify({"status": "ok", "message": "Quart Server (fix attempt) is online!"})

print("--- server/main.py: END of module definition ---")

# The if __name__ == '__main__' block for direct testing is not crucial here,
# as the main test will be done via app_launcher.py