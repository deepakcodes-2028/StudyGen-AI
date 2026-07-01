import os
import fitz
from dotenv import load_dotenv
from rag_engine import StudyGenRAGEngine

def create_mock_pdf(filename="test_sample.pdf"):
    print(f"Creating mock PDF: {filename}...")
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page()
    rect1 = fitz.Rect(50, 50, 550, 750)
    text1 = """
    StudyGen AI Project Overview
    StudyGen AI is an AI-powered PDF Study Assistant. It helps students and educators study from digital PDF notes, lecture slides, and textbooks.
    
    Key Features of the application include:
    1. Upload and processing of PDF documents page by page.
    2. Interactive RAG Chat allowing users to ask context-based questions.
    3. Generating concise AI summaries and study notes.
    4. Creating multiple-choice practice quizzes.
    5. Generating interactive 3D flashcards.
    6. Exporting and downloading generated study material in Markdown.
    
    The backend architecture utilizes Flask for server routing, PyMuPDF for PDF extraction, ChromaDB as a local vector database, and the Google Gemini API for intelligent response generation.
    """
    page1.insert_textbox(rect1, text1.strip())
    
    # Page 2
    page2 = doc.new_page()
    rect2 = fitz.Rect(50, 50, 550, 750)
    text2 = """
    Retrieval-Augmented Generation (RAG) Details
    StudyGen AI utilizes a RAG approach to answer questions accurately and avoid hallucinations.
    When a PDF is uploaded, text is chunked into overlapping segments of 600 characters with 100 characters overlap.
    A local embedding model (Sentence Transformers - all-MiniLM-L6-v2) converts the text chunks into 384-dimensional vector embeddings.
    ChromaDB stores these embeddings locally in the workspace directory 'chroma_store'.
    During a query, ChromaDB retrieves the top 4 most relevant text passages.
    These passages are fed into the Google Gemini 2.5 Flash model as context to generate accurate responses.
    """
    page2.insert_textbox(rect2, text2.strip())
    
    doc.save(filename)
    doc.close()
    print("Mock PDF created successfully.")

def main():
    load_dotenv()
    
    # Check Gemini API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[WARNING] GEMINI_API_KEY is not set in the environment or .env file.")
        print("We can test document chunking and local indexing, but Gemini model queries will fail.")
    else:
        print("[INFO] GEMINI_API_KEY found.")
        
    pdf_filename = "test_sample.pdf"
    create_mock_pdf(pdf_filename)
    
    # Initialize engine
    print("\nInitializing StudyGen RAG Engine...")
    engine = StudyGenRAGEngine(persist_directory="test_chroma_store")
    
    # Test Indexing
    print("\nTesting PDF indexing...")
    try:
        doc_id = "test_doc"
        meta = engine.index_pdf(pdf_filename, doc_id)
        print("Indexing Success!")
        print(f"Metadata: {meta}")
    except Exception as e:
        print(f"Indexing Failed: {str(e)}")
        return
        
    # Test Chroma Querying (Local Similarity Search)
    print("\nTesting ChromaDB similarity query...")
    try:
        collection_name = f"doc_{doc_id}"
        collection = engine.chroma_client.get_collection(
            name=collection_name,
            embedding_function=engine.embedding_function
        )
        results = collection.query(
            query_texts=["What is the vector dimension and embedding model used?"],
            n_results=1
        )
        print("Chroma Query Success!")
        print(f"Retrieved Chunk: {results['documents'][0][0]}")
        print(f"Source Page: {results['metadatas'][0][0]['page']}")
    except Exception as e:
        print(f"Chroma Query Failed: {str(e)}")
        
    # Test Gemini RAG response if API key is present
    if api_key:
        print("\nTesting Gemini RAG query response...")
        try:
            query = "Explain what embedding model is used in StudyGen AI and its dimension."
            res = engine.query_document(doc_id, query)
            print("Gemini RAG Query Success!")
            print(f"Question: {query}")
            print(f"Answer:\n{res['answer']}")
            print(f"References: {res['sources']}")
        except Exception as e:
            print(f"Gemini RAG Query Failed: {str(e)}")
            
        print("\nTesting Summary Generation...")
        try:
            summary = engine.generate_summary(doc_id)
            print("Summary Generation Success!")
            print(f"Summary Text Preview:\n{summary[:300]}...")
        except Exception as e:
            print(f"Summary Generation Failed: {str(e)}")
            
        print("\nTesting Quiz Generation...")
        try:
            quiz = engine.generate_quiz(doc_id)
            print("Quiz Generation Success!")
            print(f"Generated {len(quiz['questions'])} Quiz Questions.")
            print(f"Sample Question: {quiz['questions'][0]['question']}")
        except Exception as e:
            print(f"Quiz Generation Failed: {str(e)}")
            
        print("\nTesting Flashcards Generation...")
        try:
            cards = engine.generate_flashcards(doc_id)
            print("Flashcards Generation Success!")
            print(f"Generated {len(cards['cards'])} flashcards.")
            print(f"Sample Card Front: {cards['cards'][0]['front']}")
        except Exception as e:
            print(f"Flashcards Generation Failed: {str(e)}")
            
    # Clean up test files
    if os.path.exists(pdf_filename):
        os.remove(pdf_filename)
        
    print("\nVerification complete.")

if __name__ == "__main__":
    main()
