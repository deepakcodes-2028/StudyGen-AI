import os
import re
import json
import fitz
import numpy as np
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List


class QuizQuestion(BaseModel):
    question: str = Field(description="The multiple choice question based on the document context.")
    options: List[str] = Field(description="Exactly 4 options for the answer.")
    answer: str = Field(description="The correct option letter: A, B, C, or D.")
    explanation: str = Field(description="Detailed explanation of why this answer is correct.")


class QuizModel(BaseModel):
    questions: List[QuizQuestion]


class Flashcard(BaseModel):
    front: str = Field(description="The key term, concept, or question for the front of the card.")
    back: str = Field(description="The definition or explanation for the back of the card.")


class FlashcardModel(BaseModel):
    cards: List[Flashcard]


class StudyGenRAGEngine:
    def __init__(self, persist_directory="chroma_store"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        self._client = None

    def get_gemini_client(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please add it to your environment variables.")
        if self._client is None:
            self._client = genai.Client(api_key=api_key)
        return self._client

    def _get_embeddings(self, texts):
        """Get embeddings for a list of texts via Gemini API."""
        client = self.get_gemini_client()
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=texts
        )
        if not response.embeddings:
            return []
        return [e.values for e in response.embeddings]

    def _doc_path(self, doc_id):
        return os.path.join(self.persist_directory, f"doc_{doc_id}.json")

    def extract_and_chunk_pdf(self, pdf_path, chunk_size=600, overlap=100):
        doc = fitz.open(pdf_path)
        chunks = []
        metadatas = []

        for page_idx, page in enumerate(doc):
            page_text = page.get_text()
            page_num = page_idx + 1

            page_text = re.sub(r'\s+', ' ', page_text).strip()
            if not page_text:
                continue

            start = 0
            while start < len(page_text):
                end = start + chunk_size
                chunk = page_text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                    metadatas.append({
                        "page": page_num,
                        "source": os.path.basename(pdf_path)
                    })
                start += chunk_size - overlap

        return chunks, metadatas, len(doc)

    def index_pdf(self, pdf_path, document_id):
        chunks, metadatas, page_count = self.extract_and_chunk_pdf(pdf_path)
        if not chunks:
            raise ValueError("No extractable text found in the PDF.")

        # Get embeddings in batches to avoid API limits
        all_embeddings = []
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_embeddings = self._get_embeddings(batch)
            all_embeddings.extend(batch_embeddings)

        # Persist to a lightweight JSON file
        data = {
            "document_id": document_id,
            "filename": os.path.basename(pdf_path),
            "pages": page_count,
            "chunks": chunks,
            "metadatas": metadatas,
            "embeddings": all_embeddings
        }
        with open(self._doc_path(document_id), 'w', encoding='utf-8') as f:
            json.dump(data, f)

        return {
            "document_id": document_id,
            "filename": os.path.basename(pdf_path),
            "pages": page_count,
            "chunks": len(chunks)
        }

    def _load_doc(self, document_id):
        path = self._doc_path(document_id)
        if not os.path.exists(path):
            raise ValueError(f"Document '{document_id}' not found. Please re-upload your PDF.")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _cosine_similarity(self, query_vec, matrix):
        """Compute cosine similarity between a vector and a matrix of vectors."""
        query_vec = np.array(query_vec, dtype=np.float32)
        matrix = np.array(matrix, dtype=np.float32)
        dot_products = matrix @ query_vec
        query_norm = np.linalg.norm(query_vec)
        matrix_norms = np.linalg.norm(matrix, axis=1)
        return dot_products / (matrix_norms * query_norm + 1e-10)

    def query_document(self, document_id, query, k=4):
        data = self._load_doc(document_id)

        # Embed the query
        query_embedding = self._get_embeddings([query])[0]

        # Find top-k chunks by cosine similarity
        similarities = self._cosine_similarity(query_embedding, data["embeddings"])
        top_k_indices = np.argsort(similarities)[-k:][::-1]

        context_parts = []
        sources = []
        for idx in top_k_indices:
            chunk = data["chunks"][idx]
            meta = data["metadatas"][idx]
            page_num = meta.get("page", "unknown")
            context_parts.append(f"[Page {page_num}]: {chunk}")
            sources.append({"page": page_num, "content": chunk})

        context = "\n\n".join(context_parts)

        prompt = f"""You are an expert AI study assistant. Answer the user's question accurately based ONLY on the provided document context.
If the answer cannot be found in the context, say so clearly. Do not make up facts.

Document Context:
{context}

Question:
{query}

Answer clearly using Markdown. Mention page numbers when citing information.
"""
        client = self.get_gemini_client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return {"answer": response.text, "sources": sources}

    def get_full_document_text(self, document_id):
        data = self._load_doc(document_id)
        return "\n\n".join(data["chunks"])

    def generate_summary(self, document_id):
        full_text = self.get_full_document_text(document_id)
        if not full_text:
            return "No text available to summarize."

        text_context = full_text[:100000]

        prompt = f"""You are an expert academic summarizer. Generate a comprehensive and well-structured summary of the following document.

Format the output in Markdown with these sections:
- **Title**: A suitable academic title
- **Executive Summary**: A brief overview (3-4 sentences)
- **Key Concepts & Explanations**: Main concepts with short definitions
- **Detailed Takeaways**: Organized by theme or section
- **Conclusion**: Final wrap-up

Document Text:
{text_context}
"""
        client = self.get_gemini_client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text

    def generate_quiz(self, document_id):
        full_text = self.get_full_document_text(document_id)
        if not full_text:
            raise ValueError("No text available to generate a quiz.")

        text_context = full_text[:100000]

        prompt = f"""You are an educator. Generate a multiple-choice quiz with exactly 5 questions based on the document below.
Each question must have 4 choices (A, B, C, D), a correct answer letter, and a clear explanation.

Document Text:
{text_context}
"""
        client = self.get_gemini_client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QuizModel,
                temperature=0.2
            )
        )
        return json.loads(response.text)

    def generate_flashcards(self, document_id):
        full_text = self.get_full_document_text(document_id)
        if not full_text:
            raise ValueError("No text available to generate flashcards.")

        text_context = full_text[:100000]

        prompt = f"""You are a study helper. Generate exactly 6 revision flashcards from the document below.
Each flashcard needs:
1. 'front': A key term, concept, or question.
2. 'back': The definition, answer, or explanation.

Focus on the most important concepts and definitions.

Document Text:
{text_context}
"""
        client = self.get_gemini_client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FlashcardModel,
                temperature=0.3
            )
        )

        try:
            parsed = json.loads(response.text)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Invalid JSON from API: {e}. Raw: {response.text[:300]}")

        if isinstance(parsed, dict) and 'cards' in parsed:
            return parsed
        elif isinstance(parsed, list):
            return {"cards": parsed}
        else:
            for v in parsed.values():
                if isinstance(v, list):
                    return {"cards": v}
            raise ValueError(f"Unexpected response structure: {list(parsed.keys())}")
