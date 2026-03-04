from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
from openai import OpenAI
import os
import json
import logging
from pathlib import Path
from functools import lru_cache
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="../.env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


# =============================================================================
# CACHING: Load metadata once at startup to avoid expensive repeated lookups
# =============================================================================

class MetadataCache:
    """Cache for ChromaDB metadata and faculty JSON to avoid repeated lookups."""

    def __init__(self):
        self._all_metadata: Optional[Dict[str, Any]] = None
        self._faculty_json: Optional[Dict[str, Any]] = None
        self._faculty_name_index: Optional[Dict[str, str]] = None  # name -> faculty_id

    def load_chromadb_metadata(self, collection) -> Dict[str, Any]:
        """Load and cache all ChromaDB metadata. Called once at startup."""
        if self._all_metadata is None:
            logger.info("Loading ChromaDB metadata into cache...")
            try:
                self._all_metadata = collection.get(include=["documents", "metadatas"])
                doc_count = len(self._all_metadata.get('documents', []))
                logger.info(f"Cached {doc_count} documents from ChromaDB")
            except Exception as e:
                logger.error(f"Failed to load ChromaDB metadata: {e}")
                self._all_metadata = {'documents': [], 'metadatas': []}
        return self._all_metadata

    def load_faculty_json(self) -> Dict[str, Any]:
        """Load and cache faculty.json for structured lookups."""
        if self._faculty_json is None:
            faculty_json_path = Path(__file__).parent / ".." / "data" / "faculty.json"
            if faculty_json_path.exists():
                logger.info("Loading faculty.json into cache...")
                try:
                    with open(faculty_json_path, 'r', encoding='utf-8') as f:
                        self._faculty_json = json.load(f)
                    faculty_count = len(self._faculty_json.get('faculty', {}))
                    logger.info(f"Cached {faculty_count} faculty records from faculty.json")

                    # Build name index for fast lookups
                    self._build_name_index()
                except Exception as e:
                    logger.error(f"Failed to load faculty.json: {e}")
                    self._faculty_json = {'faculty': {}}
            else:
                logger.warning(f"faculty.json not found at {faculty_json_path}")
                self._faculty_json = {'faculty': {}}
        return self._faculty_json

    def _build_name_index(self):
        """Build index mapping name variations to faculty IDs."""
        self._faculty_name_index = {}
        for faculty_id, faculty in self._faculty_json.get('faculty', {}).items():
            name = faculty.get('name', '')
            # Index full name
            self._faculty_name_index[name.lower()] = faculty_id
            # Index name parts (first name, last name)
            for part in name.split():
                part_lower = part.lower().strip('.')
                if len(part_lower) > 2:  # Skip initials
                    if part_lower not in self._faculty_name_index:
                        self._faculty_name_index[part_lower] = faculty_id

    def get_faculty_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Look up faculty by name (full or partial)."""
        if self._faculty_json is None:
            self.load_faculty_json()

        name_lower = name.lower().strip()
        faculty_id = self._faculty_name_index.get(name_lower)
        if faculty_id:
            return self._faculty_json['faculty'].get(faculty_id)
        return None

    def refresh(self, collection):
        """Force refresh of all caches. Call after data re-ingestion."""
        logger.info("Refreshing metadata cache...")
        self._all_metadata = None
        self._faculty_json = None
        self._faculty_name_index = None
        self.load_chromadb_metadata(collection)
        self.load_faculty_json()


# Global cache instance
metadata_cache = MetadataCache()

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

# Initialize caches at startup
metadata_cache.load_chromadb_metadata(collection)
metadata_cache.load_faculty_json()

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
    """Health check endpoint with cache status."""
    cache_status = {
        "chromadb_cached": metadata_cache._all_metadata is not None,
        "faculty_json_cached": metadata_cache._faculty_json is not None,
    }
    if metadata_cache._all_metadata:
        cache_status["cached_docs"] = len(metadata_cache._all_metadata.get('documents', []))
    if metadata_cache._faculty_json:
        cache_status["cached_faculty"] = len(metadata_cache._faculty_json.get('faculty', {}))

    return {
        "status": "healthy",
        "collection_count": collection.count(),
        "cache": cache_status
    }


@app.post("/refresh-cache")
async def refresh_cache():
    """Refresh the metadata cache. Call after data re-ingestion."""
    try:
        metadata_cache.refresh(collection)
        return {
            "status": "success",
            "message": "Cache refreshed",
            "cached_docs": len(metadata_cache._all_metadata.get('documents', [])),
            "cached_faculty": len(metadata_cache._faculty_json.get('faculty', {}))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache refresh failed: {str(e)}")


@app.get("/rankings")
async def get_rankings():
    """
    Get faculty research rankings data for the rankings page.
    Returns overall rankings and rankings by category.
    """
    import json
    from pathlib import Path

    rankings_file = Path("../data/rankings.json")

    if rankings_file.exists():
        with open(rankings_file, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # Return empty structure if rankings haven't been generated yet
        return {
            "updated": None,
            "overall": [],
            "categories": {},
            "message": "Rankings are being generated. Please check back soon."
        }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Detect follow-up responses like "yes", "sure", "more" and use previous topic
        follow_up_phrases = {
            "yes", "yeah", "yep", "sure", "ok", "okay", "please", "more",
            "show more", "yes please", "show me more", "tell me more",
            "yes i would", "yes please show me more", "go ahead"
        }

        query_for_search = request.message

        # If this looks like a follow-up, use the previous user message for context
        if request.message.lower().strip().rstrip('.!') in follow_up_phrases:
            if request.conversation_history:
                # Find the last substantive user message (not another follow-up)
                for msg in reversed(request.conversation_history):
                    if msg.get('role') == 'user':
                        prev_msg = msg.get('content', '').lower().strip()
                        if prev_msg not in follow_up_phrases:
                            query_for_search = msg.get('content', request.message)
                            break

        # Query ChromaDB for relevant faculty information
        results = collection.query(
            query_texts=[query_for_search],
            n_results=12  # Increased to get more results for "show more" requests
        )

        # Secondary search: check if any word in the query matches a faculty name in metadata
        # This catches first-name-only or last-name-only queries that vector search may miss
        query_words = [w.lower().strip(",.?!") for w in request.message.split() if len(w) > 2]
        # Exclude common words that would cause false matches
        stop_words = {"tell", "about", "what", "who", "does", "the", "this", "that", "from",
                      "with", "have", "been", "their", "there", "which", "where", "when",
                      "faculty", "member", "professor", "research", "work", "study", "studies",
                      "expert", "institute", "water", "please", "help", "know", "information"}
        query_words = [w for w in query_words if w not in stop_words]

        name_matched_docs = []
        if query_words:
            try:
                # Use cached metadata instead of querying on every request
                all_metadata = metadata_cache.load_chromadb_metadata(collection)
                for doc, metadata in zip(all_metadata['documents'], all_metadata['metadatas']):
                    if metadata.get('type') == 'faculty':
                        source_name = metadata.get('source', '').lower()
                        name_parts = source_name.split()
                        if any(qw in name_parts for qw in query_words):
                            name_matched_docs.append((doc, metadata))
            except Exception as e:
                logger.warning(f"Name matching failed: {e}")
                pass  # Fall back to vector search only if metadata search fails

        # Build context from retrieved documents
        context = ""
        sources = []
        seen_ids = set()

        # Add vector search results first
        if results['documents'] and results['documents'][0]:
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                doc_id = f"{metadata.get('source', '')}_{metadata.get('chunk', '')}"
                if doc_id not in seen_ids:
                    context += f"\n\n{doc}"
                    seen_ids.add(doc_id)
                    if 'source' in metadata and metadata['source'] not in sources:
                        sources.append(metadata['source'])

        # Add name-matched results that weren't already included
        for doc, metadata in name_matched_docs:
            doc_id = f"{metadata.get('source', '')}_{metadata.get('chunk', '')}"
            if doc_id not in seen_ids:
                context += f"\n\n{doc}"
                seen_ids.add(doc_id)
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

                STAY ON TOPIC: You are ONLY allowed to answer questions that are directly about:
                - The UF Water Institute (mission, history, programs, facilities, partnerships, events)
                - UF Water Institute faculty members (their research, publications, contact info)
                - Water-related research at UF

                IMPORTANT: If the context below contains faculty profile data that matches a name
                in the user's question, the question IS on-topic — answer it using that context.
                A user asking about a person by first name, last name, or full name is always
                a valid faculty query.

                You must REFUSE requests that are clearly unrelated to the institute, such as:
                - General knowledge questions (e.g., "What is the meaning of life?")
                - Creative writing (e.g., "Write me a poem")
                - Math, coding, or homework help
                - Opinions, advice, or recommendations unrelated to the institute

                For ANY off-topic request, respond ONLY with:
                "I'm designed to help with questions about the UF Water Institute. Feel free to ask
                about our faculty, research, programs, or anything else related to the institute!"
                Do NOT attempt to answer the off-topic question in any way.

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

                Only include links if the faculty member's Website or Google Scholar URL appears verbatim
                in the context. If a faculty member has no URL in the context, do NOT include any link
                for them — not even a guess based on their email or name. Do not include full bios or
                publication lists unless the user asks for more detail about a specific person.

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

                TOP RESEARCHER QUERIES: When users ask about top researchers, leading experts, or
                best faculty in a specific area:

                1. Use the "Research Impact Score" from the context to rank faculty (higher is better)
                   but DO NOT show the score to users - use it only for internal ranking
                2. ALWAYS show exactly 3 researchers initially (not 1, not 2 - always 3)
                3. Format like this:
                   "Here are the top researchers in [field] at the Water Institute:
                   1. **Name** – Department. Brief expertise summary.
                      [Website](URL) | [Google Scholar](URL)
                   2. **Name** – Department. Brief expertise summary.
                      [Website](URL) | [Google Scholar](URL)
                   3. **Name** – Department. Brief expertise summary.
                      [Website](URL) | [Google Scholar](URL)"

                4. IMPORTANT: For each researcher listed, check the context for their Website and
                   Google Scholar URLs. If available, include them on a separate line directly below
                   their entry. Only include links that appear EXACTLY in the context - never guess URLs.
                   If a researcher has only one link type, show only that one. If neither exists, omit the links line.

                5. After showing the 3 researchers, ALWAYS ask: "Would you like to see more researchers in this area?"

                6. If the user asks for "more", "full list", "all researchers", "show more", or says "yes":
                   - Look for the "Additional researchers" section in the context
                   - Show ALL remaining researchers from both the main list and the additional section
                   - Include Website/Google Scholar links for each where available
                   - Format each additional researcher the same way as the initial 3

                7. If comparing researchers across different fields, note that the Field Citation Ratio
                   (FCR) is the fairest comparison metric (1.0 = field average, higher is better)

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
