from flask import Blueprint, request, render_template, send_file, jsonify
import io
import math
import base64
import traceback
from PIL import Image, ImageDraw

photosheet_bp = Blueprint("photosheet", __name__)

metadata = {
    "title": "Smart Passport Photo Sheet Generator",
    "description": "Upload multiple passport photos, set copies per person, and compile a print-ready photo sheet.",
    "image": "pages/photosheet.jpg"
}

DPI = 300  

def inches_to_px(inches, dpi=DPI):
    return int(round(inches * dpi))

def mm_to_px(mm, dpi=DPI):
    return inches_to_px(mm / 25.4, dpi)

PAGE_SIZES = {
    "a4":     {"label": "A4 (210 x 297 mm)",        "width_px": mm_to_px(210),      "height_px": mm_to_px(297)},
    "4x6":    {"label": "4 x 6 inch (Photo Print)",  "width_px": inches_to_px(4),    "height_px": inches_to_px(6)},
    "5x7":    {"label": "5 x 7 inch (Photo Print)",  "width_px": inches_to_px(5),    "height_px": inches_to_px(7)},
    "letter": {"label": "US Letter (8.5 x 11 in)",   "width_px": inches_to_px(8.5),  "height_px": inches_to_px(11)},
}

PASSPORT_ASPECT_W = 4
PASSPORT_ASPECT_H = 5

COLUMN_GAP_PX = mm_to_px(3.5)   
ROW_GAP_PX = mm_to_px(0.8)      
PAGE_PADDING_PX = mm_to_px(3)   

def decode_data_url(data_url):
    if "," in data_url:
        _, encoded = data_url.split(",", 1)
    else:
        encoded = data_url
    binary = base64.b64decode(encoded)
    img = Image.open(io.BytesIO(binary))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

def build_photo_cell(img, cell_w, cell_h):
    return img.resize((cell_w, cell_h), Image.LANCZOS)

def compute_layout(page_w, page_h, columns):
    usable_w = page_w - (2 * PAGE_PADDING_PX)
    usable_h = page_h - (2 * PAGE_PADDING_PX)

    cell_w = (usable_w - (columns - 1) * COLUMN_GAP_PX) // columns
    cell_h = int(round(cell_w * PASSPORT_ASPECT_H / PASSPORT_ASPECT_W))
    
    rows_per_page = int((usable_h + ROW_GAP_PX) // (cell_h + ROW_GAP_PX))
    
    if columns == 6 and rows_per_page < 7:
        cell_h = int((usable_h - (7 - 1) * ROW_GAP_PX) // 7)
        cell_w = int(round(cell_h * PASSPORT_ASPECT_W / PASSPORT_ASPECT_H))
        rows_per_page = 7

    if cell_w <= 0 or cell_h <= 0:
        return 0, 0, 0

    return int(cell_w), int(cell_h), int(rows_per_page)

def save_lossless_png(canvas):
    buffer = io.BytesIO()
    # PNG formats use lossless compression, completely preserving high data density
    canvas.save(buffer, format="PNG", dpi=(DPI, DPI))
    buffer.seek(0)
    return buffer

@photosheet_bp.route("/photosheet", methods=["GET", "POST"])
def photosheet_main():
    if request.method == "GET":
        return render_template("photosheet.html", page_sizes=PAGE_SIZES)

    try:
        payload = request.get_json(force=True, silent=True)
        if not payload:
            return jsonify({"success": False, "error": "Invalid JSON payload."}), 400

        page_key = str(payload.get("page_size", "a4")).lower()
        columns_raw = payload.get("columns", 6)
        people = payload.get("people", [])

        if page_key not in PAGE_SIZES:
            return jsonify({"success": False, "error": f"Unsupported page size '{page_key}'."}), 400

        columns = int(columns_raw)
        if columns < 1 or columns > 20:
            return jsonify({"success": False, "error": "Columns constraint error."}), 400

        page = PAGE_SIZES[page_key]
        page_w, page_h = page["width_px"], page["height_px"]

        cell_w, cell_h, rows_per_page = compute_layout(page_w, page_h, columns)

        queue = []
        for person in people:
            data_url = person.get("cropped_image") or person.get("image")
            try:
                copies = int(person.get("copies", 1))
            except (TypeError, ValueError):
                copies = 1
            copies = max(1, min(copies, 200))

            if not data_url:
                continue
            try:
                img = decode_data_url(data_url)
            except Exception:
                continue

            cell_img = build_photo_cell(img, cell_w, cell_h)
            queue.extend([cell_img] * copies)

        if not queue:
            return jsonify({"success": False, "error": "No valid images to process."}), 400

        per_page_capacity = columns * rows_per_page
        total_pages = max(1, math.ceil(len(queue) / per_page_capacity))

        sheets = []
        idx = 0
        for _page_num in range(total_pages):
            canvas = Image.new("RGB", (page_w, page_h), "white")
            draw = ImageDraw.Draw(canvas)

            for r in range(rows_per_page):
                if idx >= len(queue):
                    break
                for c in range(columns):
                    if idx >= len(queue):
                        break
                    x = PAGE_PADDING_PX + c * (cell_w + COLUMN_GAP_PX)
                    y = PAGE_PADDING_PX + r * (cell_h + ROW_GAP_PX)
                    canvas.paste(queue[idx], (x, y))
                    draw.rectangle([x, y, x + cell_w, y + cell_h], outline="#cccccc", width=1)
                    idx += 1

            sheets.append(canvas)

        if len(sheets) == 1:
            buffer = save_lossless_png(sheets[0])
            return send_file(buffer, mimetype="image/png", as_attachment=True, download_name="passport_photo_sheet.png")
        else:
            pdf_buffer = io.BytesIO()
            # Maximum resolution save for multiple PDF pages
            sheets[0].save(pdf_buffer, format="PDF", save_all=True, append_images=sheets[1:], resolution=DPI)
            pdf_buffer.seek(0)
            return send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name="passport_photo_sheet.pdf")

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500