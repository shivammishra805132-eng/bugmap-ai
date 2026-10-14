
import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = Flask(__name__)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

CREATOR_INFO = """
You are BugMap AI, a coding and debugging assistant.
Your creator is Shivam, a computer science student building
BugMap AI to make coding and debugging easier.
If asked who created you, say Shivam.
Never claim AI-generated analysis is guaranteed to be correct.
"""

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}

    code = str(data.get("code", "")).strip()
    language = str(data.get("language", "Auto-detect")).strip()
    mode = str(data.get("mode", "debug")).strip().lower()

    if not code:
        return jsonify({
            "result": (
                "Bug: No code was provided.\n"
                "Cause: The input editor is empty.\n"
                "Fix: Paste your code and try again.\n"
                "Explanation: BugMap AI needs code or an error message to analyze."
            )
        }), 400

    if not client:
        return jsonify({
            "result": "API key nahi mili. Apni .env file check karo."
        }), 500

    if mode == "explain":
        task = f"""
Explain the following {language} code to a beginner in the requested
explanation language, which will be specified in the user's instructions.
Explain what the code does, important lines, and its expected output.
If you find a genuine bug, explain it too.
Do not invent errors if the code is valid.
"""
    else:
        task = f"""
Analyze the following code or error written in {language}.
Identify actual bugs when possible. Do not invent errors.
Keep the response concise and beginner-friendly.

Use exactly these four sections, each on its own line:

Bug: One short sentence describing the issue.
Cause: One short sentence explaining why it happens.
Fix: Provide corrected code inside a fenced code block.
Explanation: At most two short sentences.

If no bug is apparent, say so and explain any assumptions.
If the input is an error message rather than code, explain its likely cause
and provide a useful fix.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=f"""{CREATOR_INFO}

Task: {task}

Selected programming language: {language}
Requested mode: {mode}

Additional instructions:
- Use separate lines and clear headings.
- Use the selected programming language for corrected code when applicable.
- Keep the answer concise.
- Never claim that the analysis is guaranteed correct.

User input:
{code}
"""
        )

        answer = response.text or "AI se response nahi mila."

        return jsonify({"result": answer})

    except Exception:
        app.logger.exception("Gemini request failed")
        return jsonify({
            "result": (
                "Bug: AI request could not be completed.\n"
                "Cause: Gemini returned an error or is temporarily unavailable.\n"
                "Fix: Try again shortly and check the Flask terminal for details.\n"
                "Explanation: If the issue continues, verify the model availability and API quota."
            )
        }), 502


if __name__ == "__main__":
    app.run(debug=True)
