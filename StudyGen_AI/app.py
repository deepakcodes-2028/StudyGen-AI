import os
import uuid
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv
from rag_engine import StudyGenRAGEngine, _clean_error

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "studygen-secret-default")

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

rag_engine = StudyGenRAGEngine(persist_directory="chroma_store")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        original_name = secure_filename(file.filename)
        doc_id = str(uuid.uuid4())[:8]

        temp_filename = f"{doc_id}_{original_name}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)

        try:
            file.save(file_path)
            meta = rag_engine.index_pdf(file_path, doc_id)
            return jsonify({
                "success": True,
                "document_id": doc_id,
                "filename": original_name,
                "pages": meta["pages"],
                "chunks": meta["chunks"]
            })
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"error": f"Failed to process PDF: {_clean_error(e)}"}), 500

    return jsonify({"error": "Invalid file type. Only PDF files are allowed."}), 400


@app.route('/api/query', methods=['POST'])
def query_document():
    data = request.get_json() or {}
    doc_id = data.get("document_id")
    query = data.get("query")

    if not doc_id or not query:
        return jsonify({"error": "Missing document_id or query"}), 400

    try:
        result = rag_engine.query_document(doc_id, query)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": _clean_error(e)}), 500


@app.route('/api/summarize', methods=['POST'])
def summarize_document():
    data = request.get_json() or {}
    doc_id = data.get("document_id")

    if not doc_id:
        return jsonify({"error": "Missing document_id"}), 400

    try:
        summary_text = rag_engine.generate_summary(doc_id)
        return jsonify({"summary": summary_text})
    except Exception as e:
        return jsonify({"error": _clean_error(e)}), 500


@app.route('/api/quiz', methods=['POST'])
def generate_quiz():
    data = request.get_json() or {}
    doc_id = data.get("document_id")

    if not doc_id:
        return jsonify({"error": "Missing document_id"}), 400

    try:
        quiz_data = rag_engine.generate_quiz(doc_id)
        return jsonify(quiz_data)
    except Exception as e:
        return jsonify({"error": _clean_error(e)}), 500


@app.route('/api/flashcards', methods=['POST'])
def generate_flashcards():
    data = request.get_json() or {}
    doc_id = data.get("document_id")

    if not doc_id:
        return jsonify({"error": "Missing document_id"}), 400

    try:
        flashcards_data = rag_engine.generate_flashcards(doc_id)
        return jsonify(flashcards_data)
    except Exception as e:
        return jsonify({"error": _clean_error(e)}), 500


@app.route('/api/download', methods=['POST'])
def download_content():
    data = request.get_json() or {}
    doc_id = data.get("document_id")
    content_type = data.get("type")
    content = data.get("content")
    filename = data.get("filename", "study_material")

    if not doc_id or not content_type or not content:
        return jsonify({"error": "Missing required fields"}), 400

    download_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'downloads')
    os.makedirs(download_dir, exist_ok=True)

    out_filename = f"{filename.rsplit('.', 1)[0]}_{content_type}.md"
    out_path = os.path.join(download_dir, out_filename)

    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return send_file(
            out_path,
            as_attachment=True,
            download_name=out_filename,
            mimetype="text/markdown"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate download: {str(e)}"}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code
    return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
