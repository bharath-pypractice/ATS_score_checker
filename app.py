from flask import Flask, render_template, request, jsonify
import os
import PyPDF2

# safe import for optional Gemini client
try:
    import google.generativeai as genai
except Exception:
    genai = None

# -------------------------------
# Flask app
# -------------------------------
app = Flask(__name__)

# -------------------------------
# Configure Gemini (optional)
# Read API key from environment variable `GEMINI_API_KEY`
# -------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if genai is not None and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        # if configuration fails, disable genai usage
        genai = None

# -------------------------------
# Store resume text globally
# -------------------------------
resume_text_store = ""

# -------------------------------
# PDF Reader
# -------------------------------
def extract_text_from_pdf(file):
    text = ""
    reader = PyPDF2.PdfReader(file)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

# -------------------------------
# ATS Score
# -------------------------------
def calculate_ats_score(text):
    score = 0
    t = text.lower()

    if "@" in text:
        score += 20
    if "skills" in t:
        score += 20
    if "education" in t:
        score += 20
    if "experience" in t:
        score += 20
    if any(k in t for k in ["python", "java", "sql", "ai", "machine learning"]):
        score += 20

    return score

# -------------------------------
# Routes
# -------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/upload", methods=["POST"])
def upload():
    global resume_text_store

    pdf = request.files["resume"]
    resume_text_store = extract_text_from_pdf(pdf)
    ats = calculate_ats_score(resume_text_store)

    return jsonify({
        "status": "ok",
        "ats_score": ats
    })

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    if genai is None or not GEMINI_API_KEY:
        return jsonify({
            "error": "Generative AI is not configured. Set GEMINI_API_KEY in the environment to enable chat.",
            "reply": ""
        }), 503

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(
        f"""
You are a professional ATS Resume AI assistant.

Resume:
{resume_text_store}

User Question:
{user_message}
"""
    )

    # Some genai responses embed text differently; use `.text` when available
    reply_text = getattr(response, "text", None) or str(response)

    return jsonify({
        "reply": reply_text
    })

# -------------------------------
# Run app
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
