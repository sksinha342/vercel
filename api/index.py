from flask import Flask, render_template
import os
import sys
import importlib

# Project ki root directory ko path mein add karein
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, "templates"), 
            static_folder=os.path.join(BASE_DIR, "static"))

TOOLS_FOLDER = os.path.join(BASE_DIR, "pages")

def load_tools():
    tools_list = []
    
    if not os.path.exists(TOOLS_FOLDER):
        return []

    # Files ki list ko sort karke reverse kar diya (Latest files pehle aayengi)
    all_files = sorted(os.listdir(TOOLS_FOLDER), reverse=True)

    for file in all_files:
        if file.endswith(".py") and not file.startswith("_"):
            module_name = file[:-3] 
            
            try:
                module = importlib.import_module(f"pages.{module_name}")
                blueprint_name = f"{module_name}_bp"
                
                if hasattr(module, blueprint_name):
                    bp = getattr(module, blueprint_name)
                    app.register_blueprint(bp)

                    # Metadata Retrieval
                    metadata = getattr(module, "metadata", {
                        "title": module_name.replace("_", " ").title(),
                        "description": "Powerful Python utility tool.",
                        "image": "logo.png" # Default image
                    })

                    tools_list.append({
                        "title": metadata.get("title"),
                        "desc": metadata.get("description"),
                        "img": metadata.get("image"),
                        "url": f"/{module_name}" 
                    })
                    print(f"Successfully loaded: {module_name}")
            
            except Exception as e:
                print(f"Error loading module {module_name}: {e}")

    return tools_list

# Ek baar load karein
ALL_TOOLS = load_tools()

@app.route("/")
def index():
    return render_template("index.html", tools=ALL_TOOLS)



def handler(request, response):
    return app(request.environ, response.start_response)