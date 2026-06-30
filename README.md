# StudyGen-AI
An AI-powered PDF study assistant built with Flask, RAG, and Google Gemini API. Upload any PDF to get summaries, practice quizzes, flashcards, and contextual Q&amp;A chat.


# 📚 StudyGen AI – AI PDF Study Assistant

## About the Project

StudyGen AI is a web application developed as a college AIML project to make studying from PDF documents easier and more interactive.

Instead of reading long notes or textbooks manually, users can upload a PDF and interact with it using Artificial Intelligence. The application extracts the text from the uploaded document and uses a Retrieval-Augmented Generation (RAG) approach with the Google Gemini API to answer questions, generate summaries, create quizzes, and prepare flashcards.

The main goal of this project is to help students save time while improving their learning experience through AI.

---

## Features

- 📄 Upload PDF documents
- 💬 Ask questions about the uploaded PDF
- 📝 Generate AI-powered summaries
- ❓ Create multiple-choice quiz questions
- 🧠 Generate flashcards for quick revision
- 📥 Download generated study notes in Markdown format
- 🎨 Simple and responsive user interface

---

## Technologies Used

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Flask

### Artificial Intelligence
- Google Gemini API
- Retrieval-Augmented Generation (RAG)

### PDF Processing
- PyMuPDF

### Vector Database
- ChromaDB

### Other Libraries
- LangChain
- python-dotenv

---

## Project Structure

```
StudyGen_AI/
│
├── .env
├── requirements.txt
├── app.py
├── rag_engine.py
├── test_rag.py
│
├── templates/
│   └── index.html
│
└── static/
    ├── css/
    │   └── style.css
    │
    └── js/
        └── main.js
```

---

## Requirements

Before running the project, make sure you have the following installed:

- Python (3.10 or above)
- Visual Studio Code
- Git (optional)
- Google Gemini API Key

---

## Recommended VS Code Extensions

- Python (Microsoft)
- Pylance
- DotENV
- Markdown All in One

---

## Setup Instructions

### Step 1: Open the Project

Open the **StudyGen_AI** folder in Visual Studio Code.

---

### Step 2: Create a Virtual Environment

Open the terminal and run:

```bash
python -m venv .venv
```

Activate the environment:

**Windows**

```bash
.venv\Scripts\activate
```

---

### Step 3: Install Required Packages

```bash
pip install -r requirements.txt
```

---

### Step 4: Configure Environment Variables

Create or edit the `.env` file in the project folder.

```env
FLASK_SECRET_KEY=your_secret_key
GEMINI_API_KEY=your_gemini_api_key
```

To get your Gemini API Key:

1. Visit Google AI Studio.
2. Sign in with your Google account.
3. Create a new API Key.
4. Copy and paste it into the `.env` file.

---

### Step 5: Verify the Setup

Run:

```bash
python test_rag.py
```

If everything is configured correctly, the API connection will be verified.

---

### Step 6: Start the Application

Run:

```bash
python app.py
```

Open your browser and visit:

```
http://127.0.0.1:5000
```

Now upload a PDF and start using the application.

---

## How It Works

1. Upload a PDF document.
2. The application extracts the text.
3. The content is stored in a ChromaDB vector database.
4. Relevant information is retrieved using RAG.
5. Google Gemini generates answers based on the retrieved content.
6. Users can generate summaries, quizzes, and flashcards from the same PDF.

---

## Future Improvements

- User Login System
- Multiple PDF Support
- Voice-based Question Answering
- Multi-language Support
- Cloud Storage Integration
- Progress Tracking Dashboard

---

## Project Objective

The objective of this project is to demonstrate how Generative AI can improve learning by transforming static PDF documents into an interactive study assistant. It helps students quickly understand concepts, revise important topics, and test their knowledge using AI-generated content.

---

## Developed By

**Deepak B**  
B.Tech CSE (Artificial Intelligence & Machine Learning)

**College Mini Project – StudyGen AI**
