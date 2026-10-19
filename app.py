
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

COMMON_RULES = """
IMPORTANT RULES:
- Analyze only the source code or error message supplied by the user.
- Count source-code lines from 1, including blank lines.
- Do not count Markdown fences as source-code lines.
- Never invent bugs, line numbers, causes, fixes, or output.
- Preserve the original program's purpose and behavior where possible.
- Never claim that code was executed or tested.
- Use beginner-friendly explanations.
- Keep every bug's Problem and Cause together under that bug.
- Never create a standalone Cause section.
- Keep all numbered bugs inside the Bug Detection section.
- Do not expose API keys or environment secrets.
- Use the user's requested explanation language when specified.
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
                "Bug Detection:\n"
                "No code was provided. Paste your code and try again.\n\n"
                "Explanation:\n"
                "BugMap AI needs source code or an error message to analyze."
            )
        }), 400

    if client is None:
        return jsonify({
            "result": "API key nahi mili. Apni .env file check karo."
        }), 500

    if mode == "explain":
        task = f"""
Explain the following {language} code to a beginner.

Return these sections in EXACTLY this order:

Code Overview:
Explain what the code does.

Bug Detection:
List every genuine bug in THIS section only.
Use this exact format for every bug:

🔴 Bug 1 — Line 2: Short bug title
Problem: Explain what is wrong.
Cause: Explain why this specific bug occurs.

🔴 Bug 2 — Line 3: Short bug title
Problem: Explain what is wrong.
Cause: Explain why this specific bug occurs.

Continue numbering sequentially for every genuine bug.
Keep each bug's Problem and Cause together.
Never move Bug 2 or later bugs to another section.
Do not create a separate Cause heading.
If no genuine bug is found, clearly say so.

Corrected Lines:
For every genuine bug, use this format:

🔴 Bug 1 — Line 2
❌ Incorrect Code — Line 2:
Show the original incorrect line in a fenced code block.

✅ Correct Code — Line 2:
Show the corrected line in a fenced code block.

Repeat for every bug. Preserve the original incorrect code exactly.
Use the appropriate programming language for code blocks.
Do not invent incorrect snippets or line numbers.

Fixed Code:
Provide the complete corrected program in one fenced code block.
Include necessary imports, functions, and unchanged lines.
If no correction is needed, return the original code unchanged.

Expected Output:
Show expected output when it can reasonably be determined.
Label it as an estimate, not verified execution.
Explain dependencies and assumptions.

Explanation:
Explain the important bugs and fixes in beginner-friendly language.

{COMMON_RULES}
"""

    else:
        task = f"""
Debug the following {language} source code or error message.

Return these sections in EXACTLY this order:

Bug Detection:
Corrected Lines:
Fixed Code:
Expected Output:
Explanation:


BUG DETECTION — STRICT RULES:

- Put ALL genuine bugs inside ONE Bug Detection section.
- List every bug sequentially: Bug 1, Bug 2, Bug 3, and so on.
- Every bug title MUST start with 🔴.
- Use this exact format:

🔴 Bug 1 — Line 2: Short bug title
Problem: Explain what is wrong.

🔴 Bug 2 — Line 3: Short bug title
Problem: Explain what is wrong.

- Continue this format for every genuine bug.
- Keep every bug title and its Problem inside Bug Detection.
- NEVER put Bug 2 or any later bug inside the Cause section.
- Do not omit genuine bugs or invent bugs or line numbers.
- Count source lines starting from line 1.
- If no genuine bug is found, clearly state that.

CAUSE SECTION:

- Keep Cause as a separate section.
- Explain the general reasons behind the detected bugs.
- Do not include numbered bug titles, Bug 1, Bug 2, or Bug 3 in this section.
- Do not repeat individual bug entries in Cause.
- If useful, explain common causes in one concise paragraph.

CORRECTED LINES:
For EVERY genuine bug, use this format:

🔴 Bug 1 — Line 2

❌ Incorrect Code — Line 2:
Show the original incorrect line in a fenced code block.

✅ Correct Code — Line 2:
Show the corrected line in a fenced code block.

Repeat for every bug. Use the appropriate language label.
Preserve incorrect code exactly and keep fixes consistent with Fixed Code.
Do not invent incorrect snippets.

FIXED CODE:
Provide the COMPLETE corrected program in one fenced code block.
Include all necessary imports, functions, and unchanged lines.
Do not omit necessary code or use placeholders.
If the input is only an error message, provide an example fix
and clearly label it as an example.
If no fix is needed, return the original code unchanged.

EXPECTED OUTPUT:

EXPECTED OUTPUT:

- Show ONLY the expected program output inside this section.
- Do not include explanations, notes, disclaimers, or extra text.
- Do not write "This is an estimated output" or similar messages.
- Do not include Markdown code fences such as ```text or ```.
- Do not include headings inside the output.
- Show only the output lines, preserving their order.
- If the output cannot be determined, write:
  Cannot determine expected output from the supplied code.
- Never claim the code was actually executed.

EXPLANATION:
Explain the bugs and fixes in concise, beginner-friendly language.

{COMMON_RULES}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=f"""
{CREATOR_INFO}

Task:
{task}

Selected programming language: {language}
Requested mode: {mode}

User's source code or error message:
<user_code>
{code}
</user_code>
"""
        )

        answer = response.text or (
            "Bug Detection:\n"
            "AI did not return a response.\n\n"
            "Explanation:\n"
            "Please try again."
        )

        return jsonify({"result": answer})

    except Exception:
        app.logger.exception("Gemini request failed")

        return jsonify({
            "result": (
                "Bug Detection:\n"
                "AI request could not be completed.\n\n"
                "Explanation:\n"
                "Gemini returned an error or is temporarily unavailable. "
                "Try again and check the Flask terminal. If the issue "
                "continues, verify model availability and API quota."
            )
        }), 502


if __name__ == "__main__":
    app.run(debug=True)
