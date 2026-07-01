import os
import re
import json
import uuid
import fitz
import chromadb
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List


class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name="gemini-embedding-2"):
        self.model_name = model_name
        self.client = genai.Client()

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = [
            self.client.models.embed_content(
                model=self.model_name,
                contents=doc
            ).embeddings[0].values
            for doc in input
        ]
        return embeddings


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
        self.chroma_client = chromadb.PersistentClient(path=self.persist_directory)
        self.embedding_function = GeminiEmbeddingFunction()

    def get_gemini_client(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please add it to your .env file.")
        return genai.Client(api_key=api_key)

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

        collection_name = f"doc_{document_id}"

        try:
            self.chroma_client.delete_collection(name=collection_name)
        except Exception:
            pass

        collection = self.chroma_client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )

        ids = [f"chunk_{i}" for i in range(len(chunks))]
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            collection.add(
                documents=chunks[i:i+batch_size],
                ids=ids[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )

        return {
            "document_id": document_id,
            "filename": os.path.basename(pdf_path),
            "pages": page_count,
            "chunks": len(chunks)
        }

    def query_document(self, document_id, query, k=4):
        collection_name = f"doc_{document_id}"
        collection = self.chroma_client.get_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )

        results = collection.query(
            query_texts=[query],
            n_results=k
        )

        retrieved_docs = results['documents'][0] if results['documents'] else []
        retrieved_metadatas = results['metadatas'][0] if results['metadatas'] else []

        context_parts = []
        sources = []
        for doc, meta in zip(retrieved_docs, retrieved_metadatas):
            page_num = meta.get("page", "unknown")
            context_parts.append(f"[Page {page_num}]: {doc}")
            sources.append({"page": page_num, "content": doc})

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

        return {
            "answer": response.text,
            "sources": sources
        }

    def get_full_document_text(self, document_id):
        collection_name = f"doc_{document_id}"
        collection = self.chroma_client.get_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
        results = collection.get()

        if not results['ids']:
            return ""

        ids_and_docs = list(zip(results['ids'], results['documents']))
        ids_and_docs.sort(key=lambda x: int(x[0].split('_')[1]))

        return "\n\n".join([doc for _, doc in ids_and_docs])

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
