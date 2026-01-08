from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
from openai import OpenAI
import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="../.env")

app = FastAPI()

# CORS middleware to allow WordPress to embed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your WordPress domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="../chroma/db")
collection = chroma_client.get_or_create_collection(
    name="faculty_data",
    metadata={"hnsw:space": "cosine"}
)

# OpenAI client configured for UF Navigator
client = OpenAI(
    api_key=os.getenv("NAVIGATOR_UF_API_KEY"),
    base_url=os.getenv("NAVIGATOR_API_ENDPOINT")
)

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = []

class ChatResponse(BaseModel):
    response: str
    sources: List[str]

@app.get("/")
async def root():
    return {"status": "Water Institute Faculty Chatbot API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "collection_count": collection.count()}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Query ChromaDB for relevant faculty information
        results = collection.query(
            query_texts=[request.message],
            n_results=3  # Get top 3 most relevant chunks
        )

        # Build context from retrieved documents
        context = ""
        sources = []
        if results['documents'] and results['documents'][0]:
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                context += f"\n\n{doc}"
                if 'source' in metadata and metadata['source'] not in sources:
                    sources.append(metadata['source'])

        # Build conversation messages
        messages = [
            {
                "role": "system",
                "content": f"""You are a helpful assistant for the UF Water Institute.
                You answer questions about faculty members based on the provided information.
                Be concise, friendly, and accurate. If you don't have information to answer
                a question, politely say so and suggest contacting the Water Institute directly.

                Context about faculty members:
                {context}"""
            }
        ]

        # Add conversation history (last 5 messages to keep context manageable)
        if request.conversation_history:
            messages.extend(request.conversation_history[-5:])

        # Add current message
        messages.append({"role": "user", "content": request.message})

        # Call OpenAI API (using UF Navigator endpoint)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        answer = response.choices[0].message.content

        return ChatResponse(response=answer, sources=sources)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
