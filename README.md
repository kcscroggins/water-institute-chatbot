# UF Water Institute Faculty Chatbot

A RAG-powered chatbot that answers questions about UF Water Institute faculty members using GPT-4o and ChromaDB.

## Live Deployment

- **Frontend**: https://polite-sunshine-495327.netlify.app
- **Backend API**: https://water-institute-chatbot.onrender.com
- **GitHub Repository**: https://github.com/kcscroggins/water-institute-chatbot

## Setup Instructions

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your UF Navigator API credentials:
```
NAVIGATOR_UF_API_KEY=sk-...your_key_here
NAVIGATOR_API_ENDPOINT=https://api.ai.it.ufl.edu/v1
```

### 3. Ingest Faculty Data into ChromaDB

```bash
cd backend
python ingest_faculty.py
```

You should see output like:
```
Found 16 faculty files
Processing Mike Allen: 8 chunks
...
✅ Successfully ingested 120 chunks from 16 faculty files
```

### 4. Start the Backend Server

```bash
cd backend
python main.py
```

The API will be running at `http://localhost:8000`

### 5. Open the Frontend

Open `frontend/index.html` in a web browser, or serve it locally:

```bash
cd frontend
python -m http.server 3000
```

Then visit `http://localhost:3000`

## Testing the Chatbot

Try asking questions like:
- "What is Mike Allen's research about?"
- "Who studies water quality?"
- "Tell me about Lisa Krimsky's expertise"
- "Which faculty members work on climate change?"

## Production Deployment

This project is currently deployed using:
- **Backend**: Render.com (Free tier)
- **Frontend**: Netlify (Free tier)

### Backend Deployment (Render.com)

1. **Push code to GitHub** (already done)

2. **Create Web Service on Render**:
   - Go to [render.com](https://render.com) and sign up
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Build Command**: `pip install -r backend/requirements.txt && cd backend && python ingest_faculty.py`
     - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
     - **Branch**: `main`
     - **Plan**: Free (or $7/month Starter for always-on)

3. **Add Environment Variables** in Render dashboard:
   - `NAVIGATOR_UF_API_KEY` = Your UF Navigator API key
   - `NAVIGATOR_API_ENDPOINT` = `https://api.ai.it.ufl.edu/v1`

4. **Deploy** - Render will automatically run the ingestion script and start the server

**Note**: Free tier spins down after 15 minutes of inactivity. First request after idle takes 30-60 seconds to wake up. Upgrade to $7/month Starter plan for instant responses.

### Frontend Deployment (Netlify)

1. **Go to [netlify.com](https://netlify.com)** and sign up

2. **Deploy**:
   - Click "Add new site" → "Import an existing project"
   - Choose GitHub and select your repository
   - Configure:
     - **Base directory**: (leave empty)
     - **Publish directory**: `frontend`
     - **Build command**: (leave empty)
   - Click "Deploy site"

3. **Done!** - Netlify deploys in ~30 seconds

### WordPress Integration

Add this iframe code to your WordPress page (in "Code" or "HTML" mode):

```html
<iframe
  src="https://polite-sunshine-495327.netlify.app"
  width="100%"
  height="650px"
  frameborder="0"
  style="border: none; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);"
></iframe>
```

**Sharing Options**:
- Share your WordPress page URL (recommended for official use)
- Share the Netlify URL directly: https://polite-sunshine-495327.netlify.app

## Architecture

- **Backend**: FastAPI + ChromaDB for vector search
- **Frontend**: Vanilla HTML/CSS/JS (no dependencies)
- **AI Model**: GPT-4o via UF Navigator API (adjustable in `main.py`)
- **Vector DB**: ChromaDB (persistent storage in `chroma/db/`)
- **Hosting**: Render.com (backend) + Netlify (frontend)

## API Endpoints

- `GET /` - Health check
- `GET /health` - Check database status
- `POST /chat` - Chat endpoint
  - Request: `{"message": "your question", "conversation_history": []}`
  - Response: `{"response": "answer", "sources": ["Faculty Name"]}`

## Customization

### Change AI Model
Edit `backend/main.py` line 80:
```python
model="gpt-4o",  # Change to "gpt-4o-mini" or "gpt-4-turbo"
```

### Adjust Context Window
Edit `backend/main.py` line 56:
```python
n_results=3  # Increase for more context, decrease for faster responses
```

### Customize Colors
Edit the CSS in `frontend/index.html` to match your WordPress theme.

---

## Future Enhancement: MCP Integration

### What is MCP?

MCP (Model Context Protocol) is Anthropic's open standard for connecting AI systems to external data sources and tools in real-time. It allows your chatbot to access "live" data instead of relying on static, pre-ingested information.

### Current Limitations

**Current Setup:**
- Static data stored in ChromaDB
- Must manually re-run `ingest_faculty.py` to update information
- Limited to text files in the `data/` folder
- No real-time information

### MCP Benefits

**With MCP Integration:**
- ✅ **Live faculty data** from UF directory APIs
- ✅ **Real-time publications** from research databases (Google Scholar, ORCID)
- ✅ **Course information** from university catalogs
- ✅ **Event calendars** for faculty availability and events
- ✅ **News/announcements** from Water Institute RSS feeds
- ✅ **Grant data** from funding databases (NSF, NIH)

### Potential MCP Servers to Build

1. **UF Directory Server**
   - Pull current contact info, office hours, faculty status
   - Endpoint: UF LDAP or Directory API

2. **Publications Server**
   - Query Google Scholar, ResearchGate, ORCID for recent papers
   - Auto-update publication lists

3. **Course Catalog Server**
   - Show what courses faculty are teaching this semester
   - Link to course descriptions and schedules

4. **Calendar/Events Server**
   - Water Institute events, seminars, workshops
   - Faculty office hours and availability

5. **News Feed Server**
   - Latest Water Institute news and announcements
   - Research highlights and press releases

### Implementation Considerations

**When to Add MCP:**
- Faculty data changes frequently and needs real-time updates
- You want live features (calendar booking, publication search)
- You have access to UF APIs (directory, research databases)
- Budget allows for more robust hosting (live API calls)

**Trade-offs:**
- **Pros**: Always up-to-date, richer data, dynamic queries
- **Cons**: More complex, additional API costs, requires maintenance

### Architecture with MCP

```
┌─────────────┐
│   Frontend  │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────────┐
│   Backend   │◄────►│  MCP Servers     │
│  (FastAPI)  │      │  - UF Directory  │
└──────┬──────┘      │  - Publications  │
       │             │  - Courses       │
       ▼             │  - Events        │
┌─────────────┐      └──────────────────┘
│  ChromaDB   │
│  (Fallback) │
└─────────────┘
```

**Hybrid Approach (Recommended):**
- Keep ChromaDB for faculty bios/research descriptions (static context)
- Add MCP servers for live data (publications, courses, events)
- Use ChromaDB as fallback when APIs are unavailable

### Getting Started with MCP

1. **Read the MCP Documentation**: https://modelcontextprotocol.io
2. **Install MCP SDK**: `pip install mcp`
3. **Build a simple MCP server** (e.g., faculty directory)
4. **Integrate with FastAPI backend** to query MCP servers alongside ChromaDB
5. **Test with live data** and monitor API usage/costs

### Example MCP Server (Pseudocode)

```python
from mcp.server import Server
import requests

server = Server("uf-directory")

@server.tool()
def get_faculty_contact(name: str):
    """Get current contact info for a faculty member"""
    response = requests.get(f"https://directory.ufl.edu/api/faculty/{name}")
    return response.json()

@server.tool()
def get_recent_publications(faculty_id: str, limit: int = 5):
    """Get recent publications from Google Scholar"""
    # Query Google Scholar API
    pass
```

### Resources

- **MCP Documentation**: https://modelcontextprotocol.io
- **MCP GitHub**: https://github.com/anthropics/mcp
- **Claude MCP Guide**: https://docs.anthropic.com/claude/docs/mcp

**Note**: MCP integration is optional and can be added incrementally. The current RAG-based system works well for static faculty profiles. Consider MCP when you need real-time data or want to expand functionality beyond what's in the text files.
