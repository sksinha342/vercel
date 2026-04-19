from flask import Flask, render_template
import os
import sys
import importlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, "templates"), 
            static_folder=os.path.join(BASE_DIR, "static"))

# IMPORTANT: Add secret key for session
app.secret_key = 'your-secret-key-here-12345'  # Change this to any random string

TOOLS_FOLDER = os.path.join(BASE_DIR, "pages")

def load_tools():
    tools_list = []
    
    if not os.path.exists(TOOLS_FOLDER):
        print(f"❌ Pages folder not found at: {TOOLS_FOLDER}")
        return []

    print(f"✅ Scanning tools in: {TOOLS_FOLDER}")
    
    all_files = [f for f in os.listdir(TOOLS_FOLDER) if f.endswith(".py") and not f.startswith("_")]
    all_files.sort(reverse=True)

    for file in all_files:
        module_name = file[:-3]
        
        try:
            module = importlib.import_module(f"pages.{module_name}")
            blueprint_name = f"{module_name}_bp"
            
            if hasattr(module, blueprint_name):
                bp = getattr(module, blueprint_name)
                app.register_blueprint(bp)
                print(f"✅ Registered blueprint: {module_name}")

                metadata = getattr(module, "metadata", {})
                
                tool_info = {
                    "title": metadata.get("title", module_name.replace("_", " ").title()),
                    "desc": metadata.get("description", "Powerful Python utility tool."),
                    "img": metadata.get("image", "logo.png"),
                    "url": f"/{module_name}"
                }
                tools_list.append(tool_info)
                print(f"   📝 Tool: {tool_info['title']}")
            else:
                print(f"⚠️ No blueprint '{blueprint_name}' found in {module_name}")
        
        except Exception as e:
            print(f"❌ Error loading module {module_name}: {e}")

    print(f"\n📊 Total tools loaded: {len(tools_list)}")
    return tools_list

ALL_TOOLS = load_tools()

@app.route("/")
def index():
    return render_template("index.html", tools=ALL_TOOLS)

if __name__ == "__main__":
    print("\n🚀 Starting Flask Server...")
    app.run(debug=True, port=5006, host='0.0.0.0')
