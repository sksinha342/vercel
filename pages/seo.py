from flask import Blueprint, make_response
import os

seo_bp = Blueprint('seo', __name__)

# Robots.txt
@seo_bp.route('/robots.txt')
def robots_txt():
    lines = [
        "User-agent: *",
        "Disallow: /static/",
        "Allow: /",
        "Sitemap: https://sksinha342.vercel.app/sitemap.xml"
    ]
    response = make_response("\n".join(lines))
    response.headers["Content-Type"] = "text/plain"
    return response

# Fixed Automatic Sitemap
@seo_bp.route('/sitemap.xml')
def sitemap_xml():
    base_url = "https://sksinha342.vercel.app"
    
    # Homepage ko pehle add karein
    pages_xml = [f"<url><loc>{base_url}/</loc><priority>1.0</priority></url>"]

    # Pages folder ka sahi path (BASE_DIR ke hisab se)
    # Ham __file__ ka use kar rahe hain taaki path hamesha sahi mile
    current_dir = os.path.dirname(os.path.abspath(__file__)) 
    
    if os.path.exists(current_dir):
        for file in os.listdir(current_dir):
            # .py files scan karein jo tools hain (seo.py aur __init__ ko chhod kar)
            if file.endswith(".py") and not file.startswith("_") and file != "seo.py":
                tool_name = file[:-3]
                url = f"<url><loc>{base_url}/{tool_name}</loc><priority>0.8</priority></url>"
                pages_xml.append(url)

    # XML structure ko bina kisi extra space ke join karein
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    sitemap_content += "".join(pages_xml)
    sitemap_content += '</urlset>'
    
    response = make_response(sitemap_content)
    response.headers["Content-Type"] = "application/xml"
    return response

# Metadata mark karna taaki index.html isse hide kar sake
metadata = {
    "title": "SEO Service",
    "description": "System service for Search Engines",
    "image": "logo.png"
}