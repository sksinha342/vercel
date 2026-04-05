from flask import Blueprint, request, render_template, jsonify
import pikepdf
import itertools
import io

# Blueprint name matching your index.py logic
pdfcrack_bp = Blueprint("pdfcrack", __name__)

# Dashboard Metadata - Automatically picked by index.py
metadata = {
    "title": "PDF Password Finder",
    "description": "Custom length aur characters (0-9, a-z) ke combination se password recover karein.",
    "image": "pages/passfind.jpg" 
}

@pdfcrack_bp.route("/pdfcrack", methods=["GET", "POST"])
def crack_index():
    if request.method == "GET":
        return render_template("pdfcrack.html")

    # POST Logic
    file = request.files.get('pdf_file')
    chars = request.form.get('chars')         # User input: e.g., "12345"
    max_length = request.form.get('max_length') # User input: e.g., "4"

    if not file or not chars or not max_length:
        return jsonify({"status": "error", "message": "Sari fields bharna zaroori hai!"})

    try:
        max_len = int(max_length)
        pdf_bytes = file.read()
        
        # Brute-force loop
        for length in range(1, max_len + 1):
            # itertools.product combinations banata hai: (chars^length)
            for guess in itertools.product(chars, repeat=length):
                password = "".join(guess)
                try:
                    # PDF open karne ki koshish karein
                    with pikepdf.open(io.BytesIO(pdf_bytes), password=password) as pdf:
                        return jsonify({
                            "status": "success", 
                            "message": f"🏆 Password Mil Gaya: {password}"
                        })
                except pikepdf.PasswordError:
                    continue # Galat password, next try...
                except Exception:
                    continue

        return jsonify({"status": "fail", "message": "Password nahi mila. Characters badha kar ya length badha kar firse try karein."})

    except Exception as e:
        return jsonify({"status": "error", "message": f"System Error: {str(e)}"})