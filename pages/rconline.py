from flask import Blueprint, request, jsonify, render_template
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging

# Metadata for Dashboard
metadata = {
    "title": "Auto Add name in ration card",
    "description": "ration card me name add krne ka js code.",
    "image": "pages/rconline.jpg"
}

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

rconline_bp = Blueprint("rconline", __name__)

DB_CONFIG = {
    'host': 'pg-e090c05-kumarmai00123-96a6.l.aivencloud.com',
    'port': 10411,
    'database': 'defaultdb',
    'user': 'avnadmin',
    'password': 'AVNS_gXtjV0WpUv5l47Oshjy',
    'sslmode': 'require'
}

def get_conn():
    """Get database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Database connected successfully")
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_rconline_table():
    """Create table if not exists - with proper error handling"""
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Drop table if exists (to start fresh - remove this after first run)
        # cur.execute("DROP TABLE IF EXISTS rconline")
        
        # Create table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rconline (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) UNIQUE NOT NULL,
                rc_no VARCHAR(100),
                mobile VARCHAR(20),
                applicant_data JSONB,
                applicant_js TEXT,
                members_data JSONB DEFAULT '[]',
                members_js JSONB DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster search
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_rconline_user_id ON rconline(user_id);
            CREATE INDEX IF NOT EXISTS idx_rconline_rc_no ON rconline(rc_no);
        """)
        
        conn.commit()
        logger.info("Table 'rconline' created/verified successfully")
        
        # Verify table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'rconline'
            )
        """)
        table_exists = cur.fetchone()[0]
        logger.info(f"Table exists: {table_exists}")
        
        cur.close()
        
    except Exception as e:
        logger.error(f"Error creating table: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

@rconline_bp.route("/rconline", methods=["POST","GET"])
def savine():
    if request.method == "GET":
        return render_template("AUTO ADD IN RCcc.html")


@rconline_bp.route("/rconline/save", methods=["POST"])
def save_rconline():
    conn = None
    try:
        data = request.get_json()
        logger.info(f"Received save request for user_id: {data.get('user_id')}")
        
        user_id = data.get("user_id", "").strip()
        rc_no = data.get("rc_no", "").strip()
        mobile = data.get("mobile", "").strip()
        applicant = data.get("applicant", {})
        members = data.get("members", [])
        applicant_js = data.get("applicant_js", "")
        members_js = data.get("members_js", [])
        
        if not user_id:
            return jsonify({"success": False, "message": "User ID missing"}), 400
        
        # Ensure table exists before any operation
        init_rconline_table()
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id FROM rconline WHERE user_id = %s", (user_id,))
        existing = cur.fetchone()
        
        if existing:
            logger.info(f"Updating existing user: {user_id}")
            cur.execute("""
                UPDATE rconline 
                SET rc_no = %s, mobile = %s, applicant_data = %s, applicant_js = %s, 
                    members_data = %s, members_js = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (rc_no, mobile, json.dumps(applicant, ensure_ascii=False), applicant_js,
                  json.dumps(members, ensure_ascii=False), json.dumps(members_js, ensure_ascii=False), user_id))
            message = "✅ Data updated successfully with exact JS codes!"
        else:
            logger.info(f"Inserting new user: {user_id}")
            cur.execute("""
                INSERT INTO rconline (user_id, rc_no, mobile, applicant_data, applicant_js, members_data, members_js)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, rc_no, mobile, json.dumps(applicant, ensure_ascii=False), applicant_js,
                  json.dumps(members, ensure_ascii=False), json.dumps(members_js, ensure_ascii=False)))
            message = "✅ New data saved successfully with exact JS codes!"
        
        conn.commit()
        logger.info(f"Save successful for user: {user_id}")
        
        return jsonify({"success": True, "message": message})
        
    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        logger.error(f"Integrity error: {e}")
        return jsonify({"success": False, "message": f"❌ User ID already exists or duplicate entry!"}), 400
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Save error: {e}")
        return jsonify({"success": False, "message": f"❌ Error: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@rconline_bp.route("/rconline/load", methods=["GET"])
def load_rconline():
    conn = None
    try:
        user_id = request.args.get("user_id", "").strip()
        
        if not user_id:
            return jsonify({"success": False, "message": "User ID required"}), 400
        
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM rconline WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        
        if not row:
            return jsonify({"success": False, "message": "Data not found"}), 404
        
        return jsonify({
            "success": True,
            "user_id": row["user_id"],
            "rc_no": row["rc_no"],
            "mobile": row["mobile"],
            "applicant_data": row["applicant_data"],
            "members": row["members_data"]
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if conn:
            conn.close()
@rconline_bp.route("/rconline/search", methods=["GET"])
def search_rconline():
    conn = None
    try:
        user_id = request.args.get("user_id", "").strip()
        rc_no = request.args.get("rc_no", "").strip()
        
        logger.info(f"Search request - user_id: {user_id}, rc_no: {rc_no}")
        
        # Ensure table exists
        init_rconline_table()
        
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if user_id:
            cur.execute("SELECT * FROM rconline WHERE user_id = %s", (user_id,))
        else:
            cur.execute("SELECT * FROM rconline WHERE rc_no = %s", (rc_no,))
            
        row = cur.fetchone()
        
        if not row:
            logger.info(f"No data found for search criteria")
            return jsonify({"success": False, "message": "❌ Data nahi mila"}), 404
        
        logger.info(f"Data found for user: {row.get('user_id')}")
        
        # Return exact JS codes as stored from page
        members_list = row.get("members_js") or []
        
        return jsonify({
            "success": True,
            "applicant_name": row["user_id"],
            "applicant_js": row["applicant_js"],
            "members": members_list,
            "total_members": len(members_list)
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if conn:
            conn.close()

# Initialize table when module loads
try:
    init_rconline_table()
    logger.info("Database initialization complete")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")