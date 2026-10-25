
import pickle
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from llm import ask_gemini


# ==========================================
# 1. FILE PATHS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

KNOWLEDGE_DIR = BASE_DIR / "knowledge"
KNOWLEDGE_FILE = KNOWLEDGE_DIR / "ai_ml_career.txt"
INDEX_FILE = KNOWLEDGE_DIR / "faiss.index"
CHUNKS_FILE = KNOWLEDGE_DIR / "chunks.pkl"


# ==========================================
# 2. LOAD EMBEDDING MODEL
# ==========================================

print("Loading Sentence Transformer model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Embedding model loaded successfully.")


# ==========================================
# 3. LOAD KNOWLEDGE FILE
# ==========================================

def load_knowledge():
    if not KNOWLEDGE_FILE.exists():
        raise FileNotFoundError(
            f"Knowledge file not found: {KNOWLEDGE_FILE}"
        )

    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
        text = file.read().strip()

    if not text:
        raise ValueError("The knowledge file is empty.")

    return text


# ==========================================
# 4. SPLIT TEXT INTO CHUNKS
# ==========================================

def chunk_text(text, chunk_size=500, overlap=50):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    words = text.split()
    chunks = []

    step = chunk_size - overlap

    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + chunk_size])

        if chunk:
            chunks.append(chunk)

        if start + chunk_size >= len(words):
            break

    return chunks


# ==========================================
# 5. BUILD FAISS VECTOR DATABASE
# ==========================================

def build_index():
    print("Loading career knowledge...")

    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    text = load_knowledge()

    print("Splitting text into chunks...")

    chunks = chunk_text(text)

    if not chunks:
        raise ValueError("No knowledge chunks were created.")

    print(f"Created {len(chunks)} chunks.")

    print("Creating embeddings...")

    embeddings = model.encode(
        chunks,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    embeddings = np.ascontiguousarray(
        embeddings,
        dtype=np.float32
    )

    dimension = embeddings.shape[1]

    # Cosine similarity using normalized embeddings.
    index = faiss.IndexFlatIP(dimension)

    index.add(embeddings)

    faiss.write_index(index, str(INDEX_FILE))

    with open(CHUNKS_FILE, "wb") as file:
        pickle.dump(chunks, file)

    print("FAISS index created successfully.")

    return index, chunks


# ==========================================
# 6. LOAD EXISTING VECTOR DATABASE
# ==========================================

def load_index():
    if not INDEX_FILE.exists() or not CHUNKS_FILE.exists():
        print("FAISS database not found. Building a new index...")
        return build_index()

    try:
        index = faiss.read_index(str(INDEX_FILE))

        with open(CHUNKS_FILE, "rb") as file:
            chunks = pickle.load(file)

        if not isinstance(chunks, list):
            raise ValueError("Invalid chunks file.")

        if index.ntotal != len(chunks):
            raise ValueError("Index and chunks do not match.")

        expected_dimension = model.get_sentence_embedding_dimension()

        if index.d != expected_dimension:
            raise ValueError("Embedding dimensions do not match.")

        return index, chunks

    except Exception as error:
        print(f"Unable to load existing index: {error}")
        print("Rebuilding the vector database...")

        return build_index()


# ==========================================
# 7. SEARCH RELEVANT KNOWLEDGE
# ==========================================

def search_knowledge(query, top_k=3):
    if not isinstance(query, str) or not query.strip():
        return []

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    index, chunks = load_index()

    if not chunks:
        return []

    query_embedding = model.encode(
        [query.strip()],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    query_embedding = np.ascontiguousarray(
        query_embedding,
        dtype=np.float32
    )

    number_to_search = min(top_k, len(chunks))

    scores, indices = index.search(
        query_embedding,
        number_to_search
    )

    results = []

    for score, chunk_index in zip(scores[0], indices[0]):
        if 0 <= chunk_index < len(chunks):
            # Return plain text for compatibility with app.py.
            results.append(chunks[chunk_index])

    return results


# ==========================================
# 8. RAG + GEMINI ANSWER GENERATION
# ==========================================

def ask_rag(question, top_k=3):
    if not isinstance(question, str) or not question.strip():
        return "Please enter a question."

    retrieved_chunks = search_knowledge(
        question,
        top_k=top_k
    )

    if retrieved_chunks:
        context = "\n\n".join(retrieved_chunks)
    else:
        context = "No relevant information was retrieved."

    prompt = f"""
You are CareerPilot AI, an AI and career guidance assistant.

Use the retrieved knowledge when it is relevant.

RETRIEVED KNOWLEDGE:
{context}

USER QUESTION:
{question}

Instructions:
1. Explain in simple, beginner-friendly English.
2. Use bullet points and examples where useful.
3. Give practical advice for students and freshers.
4. If the retrieved information is insufficient, say so clearly.
5. Do not invent facts or claim you searched the web.
6. Answer the user's actual question.

ANSWER:
"""

    answer = ask_gemini(prompt)

    return answer
