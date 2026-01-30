"""
Script to ingest faculty and general info text files into ChromaDB vector database.
Run this once to populate the database with faculty and Water Institute information.
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

def ingest_all_data():
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

    # Paths to data directories
    faculty_dir = Path("../data/faculty_txt")
    general_dir = Path("../data/general_info")

    # Process all files
    documents = []
    metadatas = []
    ids = []

    # Process faculty files
    if faculty_dir.exists():
        faculty_files = list(faculty_dir.glob("*.txt"))
        print(f"Found {len(faculty_files)} faculty files")

        for file_path in faculty_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract faculty name from filename
            faculty_name = file_path.stem.replace('_', ' ')

            # Chunk the content
            chunks = chunk_text(content)

            print(f"Processing faculty: {faculty_name}: {len(chunks)} chunks")

            # Add each chunk to the collection, prepending faculty name for better name-based retrieval
            for chunk_idx, chunk in enumerate(chunks):
                # Ensure faculty name appears in every chunk so name searches always match
                if faculty_name.lower() not in chunk.lower():
                    chunk = f"{faculty_name}\n{chunk}"
                documents.append(chunk)
                metadatas.append({
                    "source": faculty_name,
                    "file": file_path.name,
                    "chunk": chunk_idx,
                    "type": "faculty"
                })
                ids.append(f"faculty_{file_path.stem}_{chunk_idx}")
    else:
        print(f"⚠️  Faculty directory not found: {faculty_dir}")

    # Process general info files
    if general_dir.exists():
        general_files = list(general_dir.glob("*.txt"))
        print(f"\nFound {len(general_files)} general info files")

        for file_path in general_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract topic from filename
            topic = file_path.stem.replace('_', ' ').title()

            # Chunk the content
            chunks = chunk_text(content)

            print(f"Processing general info: {topic}: {len(chunks)} chunks")

            # Add each chunk to the collection
            for chunk_idx, chunk in enumerate(chunks):
                documents.append(chunk)
                metadatas.append({
                    "source": f"Water Institute - {topic}",
                    "file": file_path.name,
                    "chunk": chunk_idx,
                    "type": "general"
                })
                ids.append(f"general_{file_path.stem}_{chunk_idx}")
    else:
        print(f"⚠️  General info directory not found: {general_dir}")

    # Add all documents to ChromaDB
    if documents:
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        faculty_count = sum(1 for m in metadatas if m.get("type") == "faculty")
        general_count = sum(1 for m in metadatas if m.get("type") == "general")
        print(f"\n✅ Successfully ingested {len(documents)} total chunks:")
        print(f"   - {faculty_count} faculty chunks")
        print(f"   - {general_count} general info chunks")
        print(f"Collection now contains {collection.count()} documents")
    else:
        print("❌ No documents to ingest")

if __name__ == "__main__":
    ingest_all_data()
