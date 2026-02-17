# UF Water Institute Chatbot

A RAG-powered chatbot that answers questions about the UF Water Institute, including faculty members, research areas, programs, facilities, and partnerships. Built with GPT-4o and ChromaDB.

## Live Deployment

- **Frontend**: https://kcscroggins.github.io/water-institute-chatbot/
- **Backend API**: https://water-institute-chatbot.onrender.com
- **GitHub Repository**: https://github.com/kcscroggins/water-institute-chatbot

## Recent Updates

### Faculty Rankings Feature (February 2026)

Added research impact rankings for Water Institute faculty based on Dimensions.ai metrics.

**New Features:**
- ✅ `backend/rank_faculty.py` - Computes composite Research Impact Scores (0-10 scale)
- ✅ `frontend/rankings.html` - Interactive rankings page
- ✅ Researcher rankings data integrated into chatbot knowledge base

**Score Components:**
- H-Index (40%): Career publication impact
- Field Citation Ratio (30%): Impact relative to field average
- Total Citations (20%): Raw citation count
- Grant Funding (10%): Research funding success

**Usage:**
```bash
cd backend
python rank_faculty.py              # Rank all faculty
python rank_faculty.py --dry-run    # Preview without saving
python rank_faculty.py --name "Matt Cohen"  # Show specific faculty ranking
```

**Top Researchers (by Research Impact Score):**
1. Andrew Zimmerman (6.4/10) - Environmental Sciences
2. David Kaplan (6.0/10) - Astronomical Sciences
3. Gerrit Hoogenboom (5.2/10) - Agricultural Sciences
4. Nancy Denslow (4.8/10) - Biological/Environmental Sciences
5. Christopher McCarty (4.7/10) - Human Society/Psychology

---

### Faculty Profile Enrichment (January 2026)

Enriched faculty profiles with detailed research information, publications, education, and awards.

**Phase 1: Google Scholar & Website URLs (97 faculty)**
- ✅ Imported Google Scholar and Website URLs from "Database Affiliate Faculty Information Version 2.xlsx"
- ✅ 97 faculty files now include direct links to their Google Scholar profiles and/or personal websites
- ✅ Created `backend/update_faculty_v2.py` script for URL import

**Phase 2: Automated Enrichment (71 faculty)**
- ✅ Enriched 71 faculty profiles with detailed information via web search
- ✅ Added: Education, Research Focus, Notable Publications, Awards, Teaching, Keywords
- ✅ Sources: UF faculty pages, department websites, and web search results

**Phase 3: Manual Enrichment (Complete)**
- ✅ Created `data/faculty_needing_enrichment.csv` to track remaining faculty
- ✅ Workflow: User provides research info → Update profile with education, publications, policy relevance → Remove from tracking CSV
- ✅ Manually enriched 298 profiles (January 23-27, 2026), including:
  - Damian C. Adams (Natural Resource Economics, Associate Dean for Research)
  - Peter N. Adams (Geological Sciences, Geomorphology)
  - Shinsuke Agehara (Horticulture, GCREC)
  - Andrea R. Albertin (Water Resources Extension)
  - Micheal S. Allen (Fisheries, NCBS Director)
  - Angélica Almeyda Zambrano (Latin American Studies, SPEC Lab)
  - Andrew H. Altieri (Coastal Ecology, Center for Coastal Solutions)
  - Yiannis Ampatzidis (Precision Agriculture, AI/Machine Learning)
  - Clyde Fraisse (Agricultural and Biological Engineering)
  - Ruth Francis-Floyd (Veterinary Medicine)
  - Peter Frederick (Wildlife Ecology and Conservation)
  - Karen Garrett (Plant Pathology, Epidemiology)
  - Sabine Grunwald (Soil and Water Sciences, Pedometrics)
  - Kirk Hatfield (Civil and Coastal Engineering)
  - Young Gu Her (Agricultural and Biological Engineering)
  - Gerrit Hoogenboom (Agricultural and Biological Engineering)
  - Basil Iannone (Forest Ecology)
  - Patrick Inglett (Soil Biogeochemistry)
  - Tracy Irani (Public Issues Education)
  - John Jaeger (Geological Sciences, Sedimentology)
  - ...and 154 more faculty profiles

**Enriched Profile Format:**
```
Name: Faculty Name
Role: Affiliate Faculty, UF Water Institute
Academic Unit: Department Name
Email: email@ufl.edu

Subject Areas:
Research area 1, Research area 2, ...

Education:
- Ph.D. Field, University (Year)
- M.S. Field, University (Year)

Research Focus:
Description of research interests and current projects...

Notable Publications:
- Publication title (Journal, Year)
- Publication title (Journal, Year)

Awards:
- Award name (Year)

Teaching:
- Course name
- Course name

Keywords:
keyword1; keyword2; keyword3; ...
```

**Current Statistics:**
- **Total Faculty Files**: 369 (in `faculty_txt/`)
- **Enriched Profiles**: 369 (71 automated + 298 manual)
- **With Google Scholar/Website**: 97+ (URLs added during enrichment)
- **Needing Enrichment**: 15 (tracked in `faculty_needing_enrichment/`)
- **Incomplete Profiles**: 84 (in `incomplete_faculty_txt/` for future addition)
- **Ranked Faculty**: 50+ (with Dimensions research metrics)

**To Update Production:**
- Run `python ingest_faculty.py` to re-ingest all profiles
- Redeploy to Render to update production (auto-deploys on push to main)

---

### Bulk Faculty Import (January 22, 2026)

Expanded faculty database from 17 detailed profiles to **369 total faculty members** using the Water Institute's affiliate faculty database.

**What's New:**
- ✅ Imported 352 new affiliate faculty members from Excel database
- ✅ Each faculty file includes: name, role, department, email, and keywords
- ✅ Preserved 17 existing detailed profiles (Cohen, Kaplan, Krimsky, etc.)
- ✅ All faculty tagged as "Affiliate Faculty, UF Water Institute"

**Next Steps:**
- Run `python ingest_faculty.py` to re-ingest all 369 faculty files
- Optionally run `python enrich_faculty.py` to add publication data via Dimensions API
- Redeploy to Render to update production

### New Feature: General Water Institute Information

The chatbot now answers questions about the entire Water Institute, not just faculty members!

**What's New:**
- ✅ Added general institute information data (`data/general_info/`)
- ✅ Populated with real public information from UF Water Institute website
- ✅ Enhanced ingestion script to process both faculty and general data
- ✅ Updated system prompt to handle broader range of questions

**New Information Available:**
- **About**: Mission, vision, history, and core functions (established 2006)
- **Research Areas**: $164M+ in active research, key themes, specialized projects
- **Programs**: Graduate Fellows Program (WIGF), HSAC, travel awards
- **Facilities**: Main office (570 Weil Hall), lab access, field sites
- **Partnerships**: UF collaborations, Duke Energy, stakeholder engagement
- **Contact**: Phone (352-392-5893), address, director info (Dr. Matt Cohen)

**Data Sources:**
All information was gathered from publicly available sources including the official UF Water Institute website (waterinstitute.ufl.edu) and related UF resources.

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

### 3. Ingest Data into ChromaDB

The chatbot uses two types of data:
- **Faculty profiles**: Located in `data/faculty_txt/` (369 faculty members)
- **General institute info**: Located in `data/general_info/` (about, research areas, programs, facilities, partnerships, contact)

```bash
cd backend
python ingest_faculty.py
```

You should see output like:
```
Found 369 faculty files
Processing faculty: Mike Allen: 8 chunks
Processing faculty: Youngho Kim: 3 chunks
...
Found 6 general info files
Processing general info: About: 5 chunks
Processing general info: Research Areas: 4 chunks
...
✅ Successfully ingested 1500+ total chunks:
   - 1400+ faculty chunks
   - 30+ general info chunks
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

### Faculty Questions:
- "What is Mike Allen's research about?"
- "Who studies water quality?"
- "Tell me about Lisa Krimsky's expertise"
- "Which faculty members work on climate change?"

### General Institute Questions:
- "What programs does the Water Institute offer?"
- "How much research funding does the Water Institute have?"
- "Where is the Water Institute located?"
- "Who is the director of the Water Institute?"
- "What are the main research areas of the Water Institute?"
- "What partnerships does the Water Institute have?"

### Rankings Questions:
- "Who are the top researchers at the Water Institute?"
- "What is Andrew Zimmerman's research impact score?"
- "Which faculty have the highest h-index?"
- "Who are the top environmental sciences researchers?"

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

**Note**: Currently on the $7/month Starter plan for always-on hosting with instant responses (no cold starts).

### Frontend Deployment (GitHub Pages)

The frontend auto-deploys via GitHub Actions on every push to `main`.

- **Workflow file**: `.github/workflows/deploy-pages.yml`
- **Publishes**: the `frontend/` directory
- **URL**: https://kcscroggins.github.io/water-institute-chatbot/

### WordPress Integration

Add this iframe code to your WordPress page (in "Code" or "HTML" mode):

```html
<iframe
  src="https://kcscroggins.github.io/water-institute-chatbot/"
  width="100%"
  height="650px"
  frameborder="0"
  style="border: none; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);"
></iframe>
```

**Sharing Options**:
- Share your WordPress page URL (recommended for official use)
- Share the GitHub Pages URL directly: https://kcscroggins.github.io/water-institute-chatbot/

## Architecture

- **Backend**: FastAPI + ChromaDB for vector search
- **Frontend**: Vanilla HTML/CSS/JS (no dependencies)
- **AI Model**: GPT-4o via UF Navigator API (adjustable in `main.py`)
- **Vector DB**: ChromaDB (persistent storage in `chroma/db/`)
- **Data**: Faculty profiles (369) + General institute info (9 topics including rankings)
- **Hosting**: Render.com (backend) + GitHub Pages (frontend)

## Data Structure

```
data/
├── faculty_txt/                        # Faculty profile information (369 total - all enriched)
│   ├── Cohen_Matt.txt                  # Director - detailed profile
│   ├── AbdElrahman_Amr.txt             # Enriched profile
│   ├── Graham_Wendy.txt                # Enriched profile
│   ├── Zimmerman_Andrew.txt            # Enriched profile
│   └── ...
│
├── general_info/                       # Water Institute general information
│   ├── about.txt                       # Mission, vision, history, core functions
│   ├── research_areas.txt              # Research themes, funding, projects
│   ├── programs.txt                    # WIGF, HSAC, travel awards
│   ├── facilities.txt                  # Office location, lab access, field sites
│   ├── partnerships.txt                # UF collaborations, stakeholders
│   ├── contact.txt                     # Address, phone, director info
│   ├── researcher_rankings_overall.txt # Top 50 researchers by impact score
│   ├── researcher_rankings_extended.txt # Full rankings with details
│   └── top_researchers.txt             # Summary of top researchers
│
├── faculty_needing_enrichment/         # Faculty profiles still needing enrichment (15 files)
│   └── ...
│
├── incomplete_faculty_txt/             # Incomplete profiles for future work (84 files)
│   └── ...
│
├── rankings.json                       # Faculty rankings data (structured)
└── faculty_needing_dimensions_review.txt # Faculty needing Dimensions data review
```

**Faculty Profile Types:**
- **Enriched profiles (369)**: Full research descriptions, publications, education, policy relevance, keywords
- **Needing enrichment (15)**: Profiles in `faculty_needing_enrichment/` awaiting completion
- **Incomplete profiles (84)**: Profiles in `incomplete_faculty_txt/` for future addition

**How It Works:**
1. Both folders are ingested into a single ChromaDB collection
2. Each chunk is tagged with metadata (`type: "faculty"` or `type: "general"`)
3. When users ask questions, ChromaDB retrieves the most relevant chunks
4. GPT-4o generates answers based on the retrieved context
5. Sources are displayed to show where the information came from

## API Endpoints

- `GET /` - Health check
- `GET /health` - Check database status
- `POST /chat` - Chat endpoint
  - Request: `{"message": "your question", "conversation_history": []}`
  - Response: `{"response": "answer", "sources": ["Faculty Name" or "Water Institute - Topic"]}`

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

## Updating Data

### Adding or Updating Faculty Profiles

1. Add or edit `.txt` files in `data/faculty_txt/`
2. Re-run the ingestion script:
   ```bash
   cd backend
   python ingest_faculty.py
   ```
3. Restart the backend server (or redeploy on Render)

### Updating General Institute Information

1. Edit the relevant `.txt` files in `data/general_info/`:
   - `about.txt` - Mission, vision, history
   - `research_areas.txt` - Research themes and projects
   - `programs.txt` - Educational programs
   - `facilities.txt` - Facilities and resources
   - `partnerships.txt` - Collaborations
   - `contact.txt` - Contact information

2. Re-run the ingestion script:
   ```bash
   cd backend
   python ingest_faculty.py
   ```

3. Restart the backend server (or redeploy on Render)

**Note**: On Render, the ingestion script runs automatically during deployment via the build command.

---

## Faculty Data Enrichment (Dimensions API)

Enrich faculty profiles with publications, grants, and citation metrics from [Dimensions.ai](https://www.dimensions.ai/).

### Setup

1. Get a Dimensions API key from your Dimensions account
2. Add to your `.env` file:
   ```
   DIMENSIONS_API_KEY=your_key_here
   ```

### Usage

```bash
cd backend

# Enrich all faculty (takes ~2-3 min due to rate limiting)
python enrich_faculty.py

# Enrich specific faculty member
python enrich_faculty.py --name "David Kaplan"

# Preview changes without saving
python enrich_faculty.py --dry-run
```

### What It Adds

For each faculty member, the script queries Dimensions and appends:

- **Citation Metrics**: Total publications, citations, h-index
- **Recent Publications**: Last 5 years, sorted by citations (with DOI links)
- **Research Grants**: Active/recent grants with funding amounts and funders

### Example Output

After running, faculty files will include a section like:

```
--- Enriched Data (Updated: 2026-01-22) ---

Dimensions Research Metrics (via Dimensions.ai):
- Total Publications: 87
- Total Citations: 3,421
- H-Index: 32
- Average Citations per Paper: 39.3

Recent Publications (from Dimensions.ai):
- Watershed hydrology and ecohydrology... *Water Resources Research* (2024) - 45 citations
  DOI: https://doi.org/10.1029/...

Research Grants (from Dimensions.ai):
- Modeling coastal wetland responses to sea level rise (2023-2026) - $450,000
  Funder: National Science Foundation
```

### After Enrichment

1. Review the updated files in `data/faculty_txt/`
2. Re-ingest: `python ingest_faculty.py`
3. Redeploy to Render (or restart local server)

### Notes

- Rate limited to 30 requests/minute (script handles this automatically)
- Searches by name + "University of Florida" affiliation
- For better matching, add ORCID IDs to faculty files in the future

---

## Future Enhancement: MCP Integration

### What is MCP?

MCP (Model Context Protocol) is Anthropic's open standard for connecting AI systems to external data sources and tools in real-time. It allows your chatbot to access "live" data instead of relying on static, pre-ingested information.

### Current Capabilities & Limitations

**Current Setup (RAG with Static Data):**
- ✅ Faculty profiles and expertise (369 faculty members - all enriched)
- ✅ General Water Institute information (mission, programs, research, facilities, partnerships)
- ✅ Static data stored in ChromaDB
- ⚠️ Must manually re-run `ingest_faculty.py` to update information
- ⚠️ Limited to text files in the `data/` folder
- ⚠️ No real-time information (events, news, course schedules)

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
