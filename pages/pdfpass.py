from flask import Blueprint, request, send_file, render_template
import pikepdf
import io

pdfpass_bp = Blueprint("pdfpass", __name__)

metadata = {
    "title": "PDF Password Manager",
    "description": "PDF mein password lagayein ya purana password hamesha ke liye hatayein.",
    "image": "logo.png" 
}

@pdfpass_bp.route("/pdfpass", methods=["GET", "POST"])
def pdf_pass_manager():
    if request.method == "GET":
        return render_template("pdfpass.html")

    file = request.files.get('pdf_file')
    password = request.form.get('password')
    action = request.form.get('action') 

    if not file or not password:
        return "File aur Password dono zaroori hain!", 400

    try:
        in_io = io.BytesIO(file.read())
        out_io = io.BytesIO()

        if action == "add":
            # --- FIXED LOGIC HERE ---
            with pikepdf.open(in_io) as pdf:
                # Encryption set karne ka sahi tarika
                enc = pikepdf.Encryption(owner=password, user=password, R=4) # R=4 is standard 128-bit
                pdf.save(out_io, encryption=enc)
            filename = "protected.pdf"

        elif action == "remove":
            try:
                with pikepdf.open(in_io, password=password) as pdf:
                    pdf.save(out_io)
                filename = "unlocked.pdf"
            except pikepdf.PasswordError:
                return "Galat Password! Dubara try karein.", 403

        out_io.seek(0)
        return send_file(out_io, mimetype='application/pdf', as_attachment=True, download_name=filename)

    except Exception as e:
        return f"Error: {str(e)}", 500