import json
import os
import re
import uuid
from typing import Dict, List

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from google import genai
from pypdf import PdfReader

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "study-sphere-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

LECTURE_STORE: Dict[str, Dict] = {}


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text)
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]


def remove_pdf_metadata_lines(text: str) -> str:
    lines = text.splitlines()
    cleaned_lines = []
    seen_counts = {}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        normalized = re.sub(r"\s+", " ", stripped)
        seen_counts[normalized] = seen_counts.get(normalized, 0) + 1

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        normalized = re.sub(r"\s+", " ", stripped)

        if re.fullmatch(r"(Page\s*\d+|\d+|[A-Z0-9\s&-]{2,})", normalized) and seen_counts.get(normalized, 0) > 1:
            continue

        if re.fullmatch(r"(Course\s*Code|Professor|Instructor|University|Department|Lecture\s*\d+|[A-Z][A-Za-z\s-]+\s*\d+)", normalized, flags=re.IGNORECASE):
            if seen_counts.get(normalized, 0) > 1:
                continue

        if re.search(r"(professor|instructor|university|department|course code|page \d+)", normalized, flags=re.IGNORECASE):
            if seen_counts.get(normalized, 0) > 1:
                continue

        cleaned_lines.append(stripped)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text(pdf_file) -> str:
    pdf_file.stream.seek(0)
    reader = PdfReader(pdf_file)
    pages = []
    for page_index, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        page_text = clean_text(raw_text)
        if page_text:
            pages.append(page_text)

    combined = "\n\n".join(pages)
    cleaned = remove_pdf_metadata_lines(combined)
    print(f"PDF extraction debug: {len(reader.pages)} pages, {len(cleaned)} chars, first 500 chars: {cleaned[:500]}")
    return cleaned


def strip_code_fences(raw_text: str) -> str:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1].strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    return cleaned.strip()


def extract_json_object(raw_text: str):
    cleaned = strip_code_fences(raw_text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(cleaned[start : end + 1])
    return json.loads(cleaned)


def parse_json_response(raw_text: str):
    return extract_json_object(raw_text)


def gemini_call(prompt: str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return getattr(response, "text", None) or str(response)


def fallback_notes(text: str, subject: str) -> Dict:
    sentences = split_sentences(text)
    filtered = []
    for sentence in sentences:
        lower = sentence.lower()
        if re.search(r"(professor|instructor|university|course code|page |department|lecture title|semester)", lower):
            continue
        if len(sentence.split()) >= 6:
            filtered.append(sentence)

    if not filtered:
        filtered = sentences[:10] if sentences else [text[:200] or "Lecture content available for revision."]

    overview = ". ".join(filtered[:3])[:500] if filtered else "This lecture focuses on the central ideas introduced in the uploaded material."
    key_concepts = []
    for sentence in filtered[:10]:
        if len(sentence.split()) < 8:
            continue
        if sentence.lower().startswith(("the lecture", "lecture", "course")):
            continue
        key_concepts.append({
            "concept": sentence[:120],
            "explanation": sentence[:220]
        })

    if len(key_concepts) < 5:
        for sentence in filtered[:10]:
            if len(sentence.split()) >= 6:
                key_concepts.append({
                    "concept": sentence[:100],
                    "explanation": sentence[:180]
                })
            if len(key_concepts) >= 5:
                break

    definitions = []
    for sentence in filtered:
        if re.search(r"\b(defined as|means|refers to|is a|are called|consists of|includes|includes the)\b", sentence, flags=re.IGNORECASE):
            term = sentence.split(" ", 1)[0][:30]
            definitions.append({
                "term": term or "Key term",
                "definition": sentence[:220]
            })
        if len(definitions) >= 5:
            break

    if not definitions:
        definitions = [{
            "term": "Key concept",
            "definition": filtered[0][:220] if filtered else "The uploaded lecture contains central concepts that should be reviewed for revision."
        }]

    exam_points = []
    for sentence in filtered[:5]:
        exam_points.append(sentence[:220])
    if len(exam_points) < 3:
        exam_points.extend([
            "Review the main ideas and examples presented in the lecture.",
            "Focus on the definitions and relationships between the core concepts.",
            "Connect the examples to the theory discussed in class."
        ])

    quiz_questions = []
    for index, sentence in enumerate(filtered[:5], start=1):
        base = sentence[:180].strip()
        distractors = [
            "A repeated document title or metadata item.",
            "A page number or course header.",
            "A general formatting detail.",
        ]
        options = [base, *distractors]
        if len(options) > 4:
            options = options[:4]
        while len(options) < 4:
            options.append("A key idea discussed in the lecture material.")
        correct_answer = options[0]
        quiz_questions.append({
            "question": f"Which statement best matches the lecture content covered in the material?",
            "options": options,
            "correct_answer": correct_answer,
            "explanation": f"This is grounded in the lecture: {base}"
        })

    while len(quiz_questions) < 5:
        quiz_questions.append({
            "question": f"Which idea is most directly supported by the lecture content in {subject or 'this course'}?",
            "options": [
                "A central concept discussed in the lecture.",
                "The professor name.",
                "The university name.",
                "A page number."
            ],
            "correct_answer": "A central concept discussed in the lecture.",
            "explanation": "The question should test the actual lecture content, not the document metadata."
        })

    return {
        "title": subject or "Lecture Revision",
        "overview": overview,
        "key_concepts": key_concepts[:10],
        "important_definitions": definitions[:5],
        "exam_points": exam_points[:5],
        "quick_recap": "The lecture focuses on the central ideas and examples presented in the uploaded material. Review the main concepts, definitions, and examples before the exam.",
        "quiz": quiz_questions[:5],
    }


def generate_notes_and_quiz(text: str, subject: str) -> Dict:
    if not text or len(text.strip()) < 30:
        return fallback_notes(text, subject)

    prompt = f"""
You are StudySphere, a lecture-focused revision assistant.

Your job is to generate revision notes and a quiz from the uploaded lecture ONLY.
Ignore document metadata such as the title, professor name, university name, course code, page numbers, headers, footers, and repeated boilerplate.
Use only the educational content in the lecture.

Subject: {subject or 'Lecture'}

Return valid JSON only using this exact schema:
{{
  "title": "lecture title or subject",
  "overview": "3 to 5 sentence explanation of what the lecture actually teaches",
  "key_concepts": [
    {{"concept": "core topic or concept", "explanation": "short student-friendly explanation"}}
  ],
  "important_definitions": [
    {{"term": "term or concept name", "definition": "definition or explanation from the lecture"}}
  ],
  "exam_points": ["important concept, method, formula, comparison, or fact students should revise"],
  "quick_recap": "concise revision summary of the actual lecture content",
  "quiz": [
    {{
      "question": "clear MCQ about a lecture concept",
      "options": ["option 1", "option 2", "option 3", "option 4"],
      "correct_answer": "exactly one option from the list",
      "explanation": "brief explanation of why the answer is correct"
    }}
  ]
}}

Rules:
1. Use only information explicitly present in the lecture text.
2. Do not invent or add textbook content.
3. Ignore professor, university, file name, course code, page numbers, and document metadata.
4. overview must be 3-5 sentences about what the lecture teaches.
5. key_concepts must contain 5-10 real lecture concepts.
6. important_definitions must contain actual definitions or important terminology from the lecture.
7. exam_points must identify concepts, procedures, formulas, comparisons, or facts worth revising.
8. quick_recap must summarize the lecture in plain language.
9. quiz must contain EXACTLY 5 MCQs and each question must be based on lecture understanding, not metadata.
10. Do not ask questions about the document title, professor, university, course code, page numbers, or headers.
11. Every question must have exactly 4 meaningful options.
12. Ensure the correct answer exactly matches one of the options.

Lecture text:
{text}
"""

    try:
        response_text = gemini_call(prompt)
        data = parse_json_response(response_text)
        if not isinstance(data, dict):
            raise ValueError("Response was not a JSON object.")

        if "quiz" not in data or not isinstance(data["quiz"], list) or len(data["quiz"]) != 5:
            raise ValueError("Quiz length invalid.")

        if not isinstance(data.get("key_concepts", []), list):
            raise ValueError("key_concepts invalid.")

        data["title"] = data.get("title") or (subject or "Lecture Revision")
        data["overview"] = data.get("overview") or "This lecture covers the core ideas and examples introduced in the uploaded material."
        data["key_concepts"] = data.get("key_concepts") or [{"concept": "Lecture topic", "explanation": "The core idea discussed in the lecture."}]
        data["important_definitions"] = data.get("important_definitions") or [{"term": "Key term", "definition": "A term discussed in the lecture."}]
        data["exam_points"] = data.get("exam_points") or ["Review the central concepts and examples in the lecture."]
        data["quick_recap"] = data.get("quick_recap") or "The lecture focuses on the main ideas and examples introduced in the uploaded material."
        return data
    except Exception:
        return fallback_notes(text, subject)


def answer_from_lecture(question: str, lecture_text: str) -> str:
    if not lecture_text:
        return "I couldn't find any uploaded lecture content to answer from."

    prompt = f"""
You are StudySphere's lecture-specific assistant.

Use ONLY the uploaded lecture text below to answer the student's question.
Do not use outside knowledge.
Do not answer from general knowledge.
If the answer is not explicitly present in the lecture, say exactly:
"I couldn't find that information in the uploaded lecture."
Ignore document metadata such as professor names, course codes, university names, page numbers, titles, headers, and footers.

Student question:
{question}

Lecture text:
{lecture_text}
"""

    try:
        response_text = gemini_call(prompt)
        answer = response_text.strip()
        if not answer:
            raise ValueError("Blank Gemini response.")
        return answer
    except Exception:
        q_tokens = re.findall(r"[A-Za-z0-9]+", question.lower())
        sentences = split_sentences(lecture_text)
        if not sentences:
            return "I couldn't find that information in the uploaded lecture."

        scored = []
        for sentence in sentences:
            sentence_tokens = set(re.findall(r"[A-Za-z0-9]+", sentence.lower()))
            score = sum(1 for token in q_tokens if token in sentence_tokens)
            if score > 0:
                scored.append((score, sentence))

        if not scored:
            return "I couldn't find that information in the uploaded lecture."

        best_sentence = max(scored, key=lambda item: item[0])[1]
        return best_sentence[:500]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/analyze", methods=["POST"])
def analyze_lecture():
    pdf_file = request.files.get("pdf")
    subject = (request.form.get("subject") or "Lecture").strip() or "Lecture"

    if not pdf_file or not pdf_file.filename:
        return jsonify({"error": "Please upload a PDF lecture to continue."}), 400

    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    try:
        lecture_text = extract_pdf_text(pdf_file)
    except Exception:
        return jsonify({"error": "The PDF could not be read. Please upload a valid lecture PDF."}), 400

    if not lecture_text:
        return jsonify({"error": "No readable text was found in the uploaded PDF."}), 400

    lecture_id = str(uuid.uuid4())
    lecture_data = {
        "subject": subject,
        "text": lecture_text,
    }
    LECTURE_STORE[lecture_id] = lecture_data
    session["lecture_id"] = lecture_id

    notes = generate_notes_and_quiz(lecture_text, subject)
    lecture_data["notes"] = notes
    lecture_data["quiz"] = notes.get("quiz", [])

    return jsonify({
        "lecture_id": lecture_id,
        "subject": subject,
        "notes": notes,
    })


@app.route("/api/ask", methods=["POST"])
def ask_lecture():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    lecture_id = payload.get("lecture_id") or session.get("lecture_id")

    if not question:
        return jsonify({"error": "Please enter a question about the lecture."}), 400

    if not lecture_id or lecture_id not in LECTURE_STORE:
        return jsonify({"error": "No active lecture is loaded. Please upload a lecture first."}), 400

    lecture = LECTURE_STORE[lecture_id]
    answer = answer_from_lecture(question, lecture.get("text", ""))

    if "chat" not in lecture:
        lecture["chat"] = []
    lecture["chat"].append({"role": "user", "content": question})
    lecture["chat"].append({"role": "assistant", "content": answer})

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
