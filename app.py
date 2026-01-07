from flask import Flask, render_template, request, jsonify
import os, re
import PyPDF2

try:
    import google.generativeai as genai
except Exception:
    genai = None

app = Flask(__name__)

# ======================
# Gemini Setup
# ======================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if genai and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    genai = None

resume_text_store = ""

# ======================
# PDF Extraction
# ======================
def extract_text_from_pdf(file):
    text = ""
    reader = PyPDF2.PdfReader(file)
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text.strip()

# ======================
# AI ATS Analysis
# ======================
def ai_ats_analysis(resume_text):
    if genai is None:
        return 0, "AI not configured"

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
You are a professional ATS (Applicant Tracking System).

Analyze the resume realistically.

Rules:
- Score from 0 to 100
- 100 is VERY rare
- Penalize weak structure, poor skills, less experience
- Give honest feedback

Output strictly:
ATS_SCORE: <number>
FEEDBACK: <short explanation>

Resume:
{resume_text}
"""

    response = model.generate_content(prompt)
    output = response.text.strip()

    score_match = re.search(r"ATS_SCORE:\s*(\d+)", output)
    feedback_match = re.search(r"FEEDBACK:\s*(.*)", output, re.S)

    score = int(score_match.group(1)) if score_match else 0
    feedback = feedback_match.group(1).strip() if feedback_match else "No feedback"

    return max(0, min(score, 100)), feedback

# ======================
# Routes
# ======================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    global resume_text_store
    pdf = request.files.get("resume")

    if not pdf:
        return jsonify({"status": "error"}), 400

    resume_text_store = extract_text_from_pdf(pdf)
    return jsonify({"status": "ok"})

@app.route("/analyze", methods=["POST"])
def analyze():
    if not resume_text_store:
        return jsonify({"status": "error", "message": "Upload resume first"}), 400

    score, feedback = ai_ats_analysis(resume_text_store)
    return jsonify({
        "status": "ok",
        "ats_score": score,
        "feedback": feedback
    })

@app.route("/chat", methods=["POST"])
def chat():
    if genai is None:
        return jsonify({"reply": "AI not configured"})

    user_msg = request.json.get("message", "")

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(f"""
You are a resume expert.

Resume:
{resume_text_store}

User Question:
{user_msg}
""")

    return jsonify({"reply": response.text})

if __name__ == "__main__":
    app.run(debug=True)
