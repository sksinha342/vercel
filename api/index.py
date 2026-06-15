import os
import sys
import importlib
from flask import Flask, render_template, jsonify
import psycopg2
from psycopg2 import OperationalError

# Local .env file ko read karne ke liye package load kar rahe hain
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# .env file ko load kiya ja raha hai (Vercel par ye automatic bypass ho jayega)
load_dotenv()

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, "templates"), 
            static_folder=os.path.join(BASE_DIR, "static"))

# AB SAARE CREDENTIALS SYSTEM ENVIRONMENT SE AA RAHE HAIN
DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'port': int(os.environ.get('DB_PORT', 10411)), # default port 10411 rakha hai agar missing ho to
    'database': os.environ.get('DB_NAME'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD')
}

app.secret_key = os.environ.get('SECRET_KEY', 'fallback-default-key-for-safety')

# ========== DATA BASE CONNECTION FUNCTION ==========
def get_db_connection():
    """डेटाबेस से सुरक्षित कनेक्शन बनाएं"""
    # Check ki kya saare zaroori variables mil rahe hain
    if not all([DB_CONFIG['host'], DB_CONFIG['database'], DB_CONFIG['user'], DB_CONFIG['password']]):
        print("❌ Error: Database configurations key environment me missing hain!")
        return None
        
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except OperationalError as e:
        print(f"❌ डेटाबेस कनेक्शन फेल: {e}")
        return None

# ========== PAGES DYNAMIC LOADING (YOUR CODE) ==========
# ... (Aapka load_tools wala code bina kisi badlav ke yahan rahega) ...
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
            else:
                print(f"⚠️ No blueprint '{blueprint_name}' found in {module_name}")
        except Exception as e:
            print(f"❌ Error loading module {module_name}: {e}")

    print(f"\n📊 Total tools loaded: {len(tools_list)}")
    return tools_list

ALL_TOOLS = load_tools()

# ========== ROUTES ==========

@app.route("/")
def index():
    return render_template("index.html", tools=ALL_TOOLS)

@app.route('/pdf-edite',methods=["GET"])
def pdf1():
    return render_template('pdf1.html')
@app.route('/save-pdf', methods=['POST'])
def save_pdf():
    # Loop back or save modified pdf blob if needed from frontend
    return jsonify({'status': 'success', 'message': 'PDF Processed successfully on server'})

# CRON JOB ROUTE: Vercel is URL ko hit karega
@app.route("/api/cron", methods=["GET"])
def daily_db_cron():
    """Daily Automatic Database Connection Route"""
    print("⏳ Cron Job Triggered: Connecting to Database...")
    conn = get_db_connection()
    
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()
            print(f"🚀 DB Connect Success! Version: {db_version}")
            
            # Aap apna regular daily database clean ya update ka query yahan daal sakte hain
            
            cursor.close()
            conn.close()
            return jsonify({"status": "success", "message": "Database connected dynamically!"}), 200
        except Exception as query_err:
            if conn: conn.close()
            return jsonify({"status": "error", "message": f"Query failed: {str(query_err)}"}), 500
    else:
        return jsonify({"status": "failed", "message": "Could not establish database connection."}), 500



if __name__ == "__main__":
    print("\n🚀 Starting Flask Server...")
    app.run(port=5006, host='0.0.0.0')