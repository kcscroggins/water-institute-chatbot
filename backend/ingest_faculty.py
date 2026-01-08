"""
Script to ingest faculty text files into ChromaDB vector database.
Run this once to populate the database with faculty information.
"""

import chromadb
from chromadb.config import Settings
import os
from pathlib import Path

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks

def ingest_faculty_files():
    # Initialize ChromaDB
    chroma_client = chromadb.PersistentClient(path="../chroma/db")

    # Create or get collection
    try:
        collection = chroma_client.delete_collection("faculty_data")
        print("Deleted existing collection")
    except:
        pass

    collection = chroma_client.create_collection(
        name="faculty_data",
        metadata={"hnsw:space": "cosine"}
    )

    # Path to faculty files
    faculty_dir = Path("../data/faculty_txt")

    # Process each faculty file
    documents = []
    metadatas = []
    ids = []

    faculty_files = list(faculty_dir.glob("*.txt"))
    print(f"Found {len(faculty_files)} faculty files")

    for idx, file_path in enumerate(faculty_files):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract faculty name from filename
        faculty_name = file_path.stem.replace('_', ' ')

        # Chunk the content
        chunks = chunk_text(content)

        print(f"Processing {faculty_name}: {len(chunks)} chunks")

        # Add each chunk to the collection
        for chunk_idx, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "source": faculty_name,
                "file": file_path.name,
                "chunk": chunk_idx
            })
            ids.append(f"{file_path.stem}_{chunk_idx}")

    # Add all documents to ChromaDB
    if documents:
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"\n✅ Successfully ingested {len(documents)} chunks from {len(faculty_files)} faculty files")
        print(f"Collection now contains {collection.count()} documents")
    else:
        print("❌ No documents to ingest")

if __name__ == "__main__":
    ingest_faculty_files()
