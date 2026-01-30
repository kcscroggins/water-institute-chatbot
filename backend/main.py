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
    return {"status": "Water Institute Chatbot API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "collection_count": collection.count()}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Query ChromaDB for relevant faculty information
        results = collection.query(
            query_texts=[request.message],
            n_results=5  # Get top 5 most relevant chunks for better matching
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
                You answer questions about the Water Institute, including faculty members, research areas,
                programs, facilities, partnerships, and general information about the institute.

                Be concise, friendly, and accurate. Use the provided context to answer questions.
                If you don't have enough information to answer a question, politely say so and
                suggest contacting the Water Institute directly at 352-392-5893.

                STRICT URL POLICY: You must NEVER generate, invent, or guess any URL. Only use URLs
                that appear word-for-word in the provided context below. If no URL is available for
                a person or topic, simply do not include a link — do not make one up.

                FLEXIBLE MATCHING: Be flexible when interpreting user queries:
                - Handle minor typos and misspellings in names (e.g., "Mathew" = "Matthew", "Kohen" = "Cohen")
                - Recognize reordered phrases (e.g., "watershed ecohydrology & hydrology" = "watershed hydrology & ecohydrology")
                - Match partial names (e.g., "Dr. Cohen" or "Matt" should match "Matthew J. Cohen")
                - Understand synonyms and related terms (e.g., "water science" ≈ "hydrology", "publications" ≈ "papers" ≈ "research")
                - If a query seems close to something in the context, make the connection and answer helpfully

                EXPERT RECOMMENDATIONS: When a user asks for an expert, specialist, or faculty member
                in a specific area, recommend the top 3 most relevant faculty. Keep it brief using this format:

                1. **Name** – Department. One-sentence summary of relevant expertise.
                2. **Name** – Department. One-sentence summary of relevant expertise.
                3. **Name** – Department. One-sentence summary of relevant expertise.

                Include links for each faculty member if available. Do not include full bios or publication lists
                unless the user asks for more detail about a specific person.

                CRITICAL REQUIREMENT - LINKS:
                1. When answering questions about a specific faculty member, you MUST include their
                Website and Google Scholar links at the END of your response. Look for lines starting with "Website:" and
                "Google Scholar:" in the context. Format them EXACTLY like this example:

                **Links:** [Website](URL_FROM_CONTEXT) | [Google Scholar](URL_FROM_CONTEXT)

                - ONLY use URLs that appear EXACTLY in the provided context. Copy them character for character.
                - If no URL exists in the context for a faculty member, do NOT include a link for them.
                - Always put links on their own line at the very end of your response
                - NEVER add filler phrases before links such as "For more information, visit...",
                  "You can learn more at...", "Feel free to check out...", or "contact the Water Institute".
                  Just end your answer naturally and place the **Links:** line directly after.
                  Example of a GOOD response:
                  "Dr. Matt Cohen is the director of the UF Water Institute. He is a professor of ecohydrology with expertise in watershed hydrology and biogeochemistry.

                  **Links:** [Website](https://ffgs.ifas.ufl.edu/ecohydrology/) | [Google Scholar](https://scholar.google.com/citations?user=cFbUqrEAAAAJ&hl=en)"

                2. When the context contains any other relevant links (e.g., program pages, application forms,
                travel awards, etc.), you MUST include those links in your response. Use the exact URLs
                from the context and format them as clickable markdown links.

                3. KNOWN LINKS - Always use these exact URLs when discussing these topics (NEVER make up URLs):
                - Travel Awards: https://waterinstitute.ufl.edu/student-travel-award/

                Relevant context:
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
