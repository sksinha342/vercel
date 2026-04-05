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
    
    # Agar pages folder nahi hai toh khali list bhejein
    if not os.path.exists(TOOLS_FOLDER):
        return []

    # Pages folder ki har .py file ko scan karein
    for file in os.listdir(TOOLS_FOLDER):
        if file.endswith(".py") and not file.startswith("_"):
            module_name = file[:-3] # Extension (.py) hatao
            
            try:
                # Module ko dynamically import karein
                # Note: pages.module_name format use ho raha hai
                module = importlib.import_module(f"pages.{module_name}")
                
                # Blueprint check karein (Jaise: doclike_bp, qrgen_bp)
                blueprint_name = f"{module_name}_bp"
                
                if hasattr(module, blueprint_name):
                    bp = getattr(module, blueprint_name)
                    app.register_blueprint(bp)

                    # --- METADATA RETRIEVAL ---
                    # Module ke andar se 'metadata' variable uthao
                    # Agar module mein metadata nahi hai, toh default values use karein
                    metadata = getattr(module, "metadata", {
                        "title": module_name.replace("_", " ").title(),
                        "description": "Powerful Python utility tool.",
                        "image": "default.png"
                    })

                    tools_list.append({
                        "title": metadata.get("title"),
                        "desc": metadata.get("description"),
                        "img": metadata.get("image"),
                        "url": f"/{module_name}" # Blueprint ka route same file name jaisa hona chahiye
                    })
                    print(f"Successfully loaded: {module_name}")
            
            except Exception as e:
                print(f"Error loading module {module_name}: {e}")

    return tools_list

# Tools ko ek baar load karein taaki har request par import na karna pade
ALL_TOOLS = load_tools()

@app.route("/")
def index():
    # Index page par 'tools' variable ke roop mein list bhej rahe hain
    return render_template("index.html", tools=ALL_TOOLS)

def handler(request, response):
    return app(request.environ, response.start_response)