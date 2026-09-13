# StudySphere

StudySphere is a Flask-based lecture-to-revision app that helps students turn uploaded lecture PDFs into AI-generated revision notes, practice quizzes, and lecture-grounded Q&A.

## Features

- Upload a lecture PDF
- Extract and clean lecture text
- Generate revision notes from the uploaded material
- Build a quiz based on the lecture content
- Ask questions grounded in the uploaded lecture
- Export notes in the browser
- Futuristic dark UI with a Knowledge Core visual theme

## Tech Stack

- Python
- Flask
- Google GenAI / Gemini
- PyPDF
- HTML, CSS, and JavaScript

## Project Structure

- `app.py` — Flask backend and AI workflows
- `templates/` — HTML views
- `static/css/` — app styling
- `static/js/` — frontend behavior
- `uploads/` — uploaded lecture files
- `requirements.txt` — Python dependencies
- `.env` — local environment variables

## Prerequisites

- Python 3.10+
- A Google Gemini API key

## Setup

1. Open a terminal in the project folder.
2. Create and activate a virtual environment:

   Windows PowerShell:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with:

   ```env
   GEMINI_API_KEY=your_api_key_here
   SECRET_KEY=your_secret_key_here
   ```

## Run the App

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000/
```

## Notes

- The app expects a valid PDF lecture file for the extraction and revision pipeline.
- The AI features rely on the `GEMINI_API_KEY` environment variable being set correctly.
- The current project is designed as a local app for demo and study workflows.
