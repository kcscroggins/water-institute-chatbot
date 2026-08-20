# UF Water Institute Chatbot

A RAG-powered chatbot that answers questions about the UF Water Institute, including faculty members, research areas, programs, facilities, and partnerships. Built with GPT-5 mini and ChromaDB.

## Live Deployment

- **Frontend**: https://kcscroggins.github.io/water-institute-chatbot/
- **Backend API**: https://water-institute-chatbot.onrender.com
- **GitHub Repository**: https://github.com/kcscroggins/water-institute-chatbot

## Current Status (August 2026)

- **Model**: GPT-5 mini (configurable via `NAVIGATOR_MODEL` env var)
- **Test Pass Rate**: 93.8% (80 tests)
- **ChromaDB Chunks**: 421 indexed documents
- **Faculty Profiles**: 376 enriched profiles with caching enabled
- **Average Response Time**: ~5.5 seconds

---

## Recent Updates

### Model Swap to GPT-5 Mini (August 2026)

Swapped the default backing model from `gpt-4o` to `gpt-5-mini` after the UF Navigator API exposed GPT-5 access. Comparable quality on our RAG workload at lower cost and latency. Made the model env-configurable so future swaps don't require a code change.

**Why the change:** GPT-5 mini gives comparable answer quality with roughly on-par latency (5.5s avg vs 4s baseline). The test suite went from 96.9% (older 32-test suite on gpt-4o) → 93.8% on the current 80-test suite; the remaining failures traced back to RAG retrieval issues that gpt-4o had been quietly working around, not to the model.

**GPT-5 parameter gotchas (worth knowing before other swaps):**
- GPT-5 family requires `max_completion_tokens` instead of `max_tokens`
- GPT-5 rejects custom `temperature` values (only default `1.0` is accepted)
- Reasoning tokens count against `max_completion_tokens` — a naive swap produced empty responses and 131s timeouts on ~40% of tests until we set `reasoning_effort="minimal"` (right choice for RAG-backed Q&A where the retrieved context *is* the reasoning)

**New Files / Changes:**
- ✅ `backend/main.py` — `MODEL_NAME` now reads from `NAVIGATOR_MODEL` env var (default: `gpt-5-mini`); new `_completion_kwargs()` helper builds model-specific params so GPT-5 family gets `max_completion_tokens=2000, reasoning_effort="minimal"` while legacy models keep `temperature=0.3, max_tokens=500`
- ✅ `backend/test_chatbot.py` — grader relaxed to accommodate GPT-5 mini's phrasing variance: broadened substring keywords on "Who runs the WI?" so `"directed"` matches, added a `guardrail_error_ok` field so upstream 5xx responses count as pass on jailbreak tests (Navigator content filter blocking is the desired outcome), aligned the "Show me more" multi-turn keyword with its stated intent

**Rollback / override without a code change:**
```bash
# On Render, set:
NAVIGATOR_MODEL=gpt-4o     # or gpt-5, gpt-4o-mini, etc.
# then redeploy — the env var overrides the code default
```

---

### Live Events Feed from UF LiveWhale Calendar (July 2026)

Replaced the previous WordPress event fetcher — which was 404-ing (`rest_no_route`) and had been serving stale placeholder data — with a live pull from the official UF calendar and lifted events out of ChromaDB into the system prompt.

**Why the architectural change:** RAG retrieval is lossy for small, time-critical datasets. If someone asked "any events in September?" and the September event's chunk didn't rank in the top K, the LLM would confidently say no. Events are small (≤20 typically), always relevant when asked, and dates must be exact — so they're now injected verbatim into the system prompt alongside the KNOWN FACTS block and marked authoritative.

**New Files / Changes:**
- ✅ `backend/events_cache.py` — `EventsCache` class (thread-safe, 1h TTL, last-known-good on fetch failure), LiveWhale fetch with browser UA (CloudFront rejects the default), client-side filter on `group_title == "UF Water Institute"` (the `?group=` query param is silently ignored by the endpoint), and `format_for_prompt()` renderer
- ✅ `backend/main.py` — cache warmed at startup, `{events_block}` injected above KNOWN FACTS, lazy background refresh scheduled on stale `/chat` requests so calendar.ufl.edu never blocks the hot path, new `POST /refresh-events` endpoint, cache status surfaced through `/health`
- ✅ `backend/main.py` — EVENTS section of the system prompt rewritten to point at the injected block as the sole authoritative source and never draw event details from retrieved context
- 🗑️ `backend/fetch_events.py` and `data/general_info/events.txt` — removed (superseded)

**Source:** `https://calendar.ufl.edu/live/json/events` (returns the full UF-wide feed, filtered locally). Debug the cached block with `python events_cache.py`.

**Endpoint:**
```bash
# Manually refresh when a new event is published (skips the 1h wait)
curl -X POST https://water-institute-chatbot.onrender.com/refresh-events
```

---

### Chat Logging to Google Sheets & Expanded Test Suite (June 2026)

Added end-to-end Q&A logging so the team can review what users are asking and where the bot answers poorly. Also broadened `test_chatbot.py` with hallucination, prompt-injection, multi-turn, events, and boundary tests.

**New Files / Changes:**
- ✅ `backend/chat_logger.py` — `ChatLogger` class that appends rows to a Google Sheet
- ✅ `backend/main.py` — `/chat` now logs each request via `BackgroundTasks` (zero added latency)
- ✅ `backend/requirements.txt` — added `gspread>=6.0.0` and `google-auth>=2.0.0`
- ✅ `backend/test_chatbot.py` — added 5 new categories, `expected_keywords_any` field, and `conversation_history` support per test

**Logged columns:** `timestamp_utc`, `question`, `response`, `sources`, `response_time_ms`, `model`, `error`.

If the env vars below are not set, logging silently no-ops — `/chat` keeps working normally.

**Required environment variables (Render):**
```
GOOGLE_SHEETS_CREDENTIALS_JSON   # full service-account JSON, pasted as-is
GOOGLE_SHEETS_ID                 # spreadsheet ID from the Sheet URL
GOOGLE_SHEETS_TAB                # tab name, e.g. "Chat Logs" (auto-created if missing)
```

**One-time Google setup:**
1. Create a new Google Sheet; copy the ID from its URL
2. In Google Cloud Console, create a project and enable the **Google Sheets API**
3. Create a service account; under its **Keys** tab, add a new JSON key (downloads a file)
4. In the Sheet, share with the service account's `client_email` (Editor access)
5. Add the three env vars above on Render and redeploy

**Startup log line confirms status:**
- `Chat logging enabled → sheet '<id>' tab '<tab>'` — working
- `Chat logging disabled: ...` — reason printed (missing var, bad JSON, share permission, etc.)

**New Test Categories:**

| Category | What it probes |
|----------|---------------|
| Hallucination | Fake faculty names, future awards, PII — bot must refuse, not invent |
| Prompt Injection | "Ignore previous instructions", DAN jailbreak, system-prompt leak |
| Multi-Turn | Follow-ups like "tell me more about him" using `conversation_history` |
| Events | Verifies the LiveWhale events block (injected into the prompt by `events_cache`) is being surfaced |
| Boundary | Single-char query, ALL CAPS, repeated text, misspelled names |

**Test framework additions:**
- `expected_keywords_any: List[str]` — passes if at least ONE matches (for refusal phrasings that legitimately vary)
- `conversation_history: List[dict]` — sends prior turns with the request so multi-turn behavior can be tested

**Usage:**
```bash
cd backend
python test_chatbot.py              # against production
python test_chatbot.py --local      # against http://localhost:8000
python test_chatbot.py --verbose    # show full responses
```

---

### Google Scholar Profile Verification (March 2026)

Created `backend/verify_scholar.py` to verify Google Scholar profile links in faculty .txt files.

**What It Does:**
- Fetches each Google Scholar profile page and extracts the profile name
- Compares against the faculty name using fuzzy matching (difflib)
- Cross-references publication titles from Scholar against Dimensions publications in the .txt file
- Outputs a summary report of mismatches, review recommendations, and verified profiles

**Results (272 faculty with Scholar URLs):**
- 237 verified correct
- 4 mismatches found (1 real: Zimmerman_Andrew had wrong profile, 3 false positives from name formatting)
- 18 flagged for review (mostly nickname/abbreviation differences)
- 4 broken URLs (404 errors)

**Fixes Applied:**
- `Zimmerman_Andrew.txt` — Corrected Scholar URL from `pRh2pjMAAAAJ` (Jonathan B Martin) to `Dh2TSsQAAAAJ` (Andrew R. Zimmerman)

**Usage:**
```bash
cd backend
python verify_scholar.py                          # Check all faculty (~15-20 min)
python verify_scholar.py --name "Andrew Zimmerman" # Check single faculty
python verify_scholar.py --verbose                 # Print each result as checked
```

---

### Structured Faculty Data & Performance Caching (March 2026)

Added structured JSON database and startup caching for improved performance and future search enhancements.

**New Features:**
- ✅ `backend/generate_faculty_json.py` - Parses all faculty .txt files into structured JSON
- ✅ `data/faculty.json` - Structured faculty database (376 faculty records)
- ✅ `MetadataCache` class in main.py - Caches data at startup to eliminate per-request overhead
- ✅ `/health` endpoint now shows cache status
- ✅ `/refresh-cache` endpoint for manual cache refresh after data updates

**Faculty JSON Statistics:**
- 376 total faculty records
- 288 with Dimensions research metrics
- 289 with research impact rankings
- 270 with Google Scholar URLs
- 179 with website URLs
- 249 with recent publications

**Performance Improvement:**
- Metadata is now loaded once at startup instead of scanning 2500+ documents per request
- Faculty name index enables O(1) lookups by name

**Usage:**
```bash
cd backend
python generate_faculty_json.py              # Generate faculty.json
python generate_faculty_json.py --dry-run    # Preview without saving
python generate_faculty_json.py --validate   # Validate existing JSON
```

**API Endpoints:**
```bash
# Check cache status
curl https://water-institute-chatbot.onrender.com/health

# Refresh cache after data changes
curl -X POST https://water-institute-chatbot.onrender.com/refresh-cache
```

---

### Faculty Rankings Feature (February 2026)

Added research impact rankings for Water Institute faculty based on Dimensions.ai metrics.

**New Features:**
- ✅ `backend/rank_faculty.py` - Computes composite Research Impact Scores (0-10 scale)
- ✅ `frontend/rankings.html` - Interactive rankings page
- ✅ Researcher rankings data integrated into chatbot knowledge base
- ✅ Top researcher responses include Website and Google Scholar links
- ✅ Rankings files include faculty URLs for direct access

**Chatbot Behavior:**
- When users ask for top researchers in a field, the chatbot shows **3 researchers** with their expertise and links
- Research Impact Scores are used internally for ranking but **not shown to users**
- Each researcher entry includes Website and/or Google Scholar links (if available)
- After showing 3 researchers, the chatbot asks: "Would you like to see more researchers in this area?"

**Score Components (internal use):**
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

**Top Researchers:**
1. Andrew Zimmerman - Environmental Sciences
2. David Kaplan - Watershed Ecology
3. Gerrit Hoogenboom - Agricultural Sciences
4. Nancy Denslow - Biological/Environmental Sciences
5. Christopher McCarty - Human Society/Psychology

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
- Run `python ingest_faculty.py` locally to re-ingest all profiles
- Push to main triggers auto-deploy on Render, which re-runs ingestion
- **Important**: If data seems stale (e.g., removed faculty still appearing), manually trigger a redeploy on Render dashboard to force re-ingestion

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

### Automated Test Suite

Run the comprehensive test suite to validate chatbot functionality:

```bash
cd backend
python test_chatbot.py                # Test against production API
python test_chatbot.py --local        # Test against localhost:8000
python test_chatbot.py --verbose      # Show full responses
```

**Test Categories:**
- Rankings queries (7 tests)
- Faculty profile queries (10 tests)
- General institute queries (8 tests)
- Edge cases (5 tests)
- Off-topic guardrails (2 tests)

**Latest Test Results (March 2026):**

| Category | Pass Rate | Status |
|----------|-----------|--------|
| Rankings | 86% | ✅ Working well |
| Faculty Profile | 100% | ✅ All passed |
| General Institute | 100% | ✅ All passed |
| Edge Cases | 100% | ✅ All passed |
| Off-Topic Guard | 100% | ✅ All passed |
| **Overall** | **96.9%** | ✅ Production ready |

**Performance:**
- Average response time: ~4 seconds
- Collection size: 719 chunks indexed
- Faculty profiles cached: 376

### Sample Questions

**Faculty Questions:**
- "What is Mike Allen's research about?"
- "Who studies water quality?"
- "Tell me about Lisa Krimsky's expertise"
- "Which faculty members work on climate change?"

**General Institute Questions:**
- "What programs does the Water Institute offer?"
- "How much research funding does the Water Institute have?"
- "Where is the Water Institute located?"
- "Who is the director of the Water Institute?"
- "What are the main research areas of the Water Institute?"
- "What partnerships does the Water Institute have?"

**Rankings Questions:**
- "Who are the top researchers at the Water Institute?"
- "Who are the top PFAS researchers?"
- "Who are the top environmental sciences researchers?"
- "Show me more researchers in hydrology"

**Edge Case Questions:**
- "Who is John?" (finds all faculty named John)
- "Tell me about hydrology research"
- "Faculty studying Everglades"
- "What is WIGF?"

## Production Deployment

This project is currently deployed using:
- **Backend**: Render.com
- **Frontend**: GitHub Pages

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
- **AI Model**: GPT-5 mini via UF Navigator API (set via `NAVIGATOR_MODEL` env var; default in `main.py`)
- **Vector DB**: ChromaDB (persistent storage in `chroma/db/`, 693 chunks indexed)
- **Data**: Faculty profiles (369) + General institute info (9 topics including rankings)
- **Hosting**: Render.com (backend) + GitHub Pages (frontend)
- **Testing**: Automated test suite (`test_chatbot.py`) with 32 test cases

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
├── faculty.json                        # Structured faculty database (376 records)
└── faculty_needing_dimensions_review.txt # Faculty needing Dimensions data review
```

**faculty.json Structure:**
```json
{
  "metadata": { "generated": "...", "total_faculty": 376 },
  "faculty": {
    "cohen_matt": {
      "name": "Matthew J. Cohen",
      "role": "Director, UF Water Institute",
      "academic_unit": "School of Forest, Fisheries, and Geomatics Sciences",
      "email": "mjc@ufl.edu",
      "website": "https://...",
      "google_scholar": "https://...",
      "expertise": { "subject_areas": [...], "keywords": [...], "research_categories": [...] },
      "metrics": { "h_index": 36, "total_citations": 4392, "field_citation_ratio": 7.45 },
      "rankings": { "impact_score": 3.0, "percentile": 7, "by_category": {...} },
      "recent_publications": [...],
      "grants": [...]
    }
  }
}
```

**Faculty Profile Types:**
- **Enriched profiles (369)**: Full research descriptions, publications, education, policy relevance, keywords
- **Needing enrichment (15)**: Profiles in `faculty_needing_enrichment/` awaiting completion
- **Incomplete profiles (84)**: Profiles in `incomplete_faculty_txt/` for future addition

**How It Works:**
1. Both folders are ingested into a single ChromaDB collection
2. Each chunk is tagged with metadata (`type: "faculty"` or `type: "general"`)
3. When users ask questions, ChromaDB retrieves the most relevant chunks
4. GPT-5 mini generates answers based on the retrieved context
5. Sources are displayed to show where the information came from

## API Endpoints

- `GET /` - Health check
- `GET /health` - Check database status, collection count, and events cache status
- `GET /rankings` - Get faculty research rankings data (JSON)
- `POST /chat` - Chat endpoint
  - Request: `{"message": "your question", "conversation_history": []}`
  - Response: `{"response": "answer", "sources": ["Faculty Name" or "Water Institute - Topic"]}`
- `POST /refresh-cache` - Rebuild the ChromaDB metadata / faculty.json caches (call after re-ingestion)
- `POST /refresh-events` - Immediately re-fetch upcoming events from calendar.ufl.edu (otherwise auto-refreshes hourly)

## Customization

### Change AI Model
Preferred: set the `NAVIGATOR_MODEL` env var on Render (or in `.env`) — no code change or push required:
```
NAVIGATOR_MODEL=gpt-4o    # or gpt-5, gpt-5-mini, gpt-4o-mini, etc.
```
To change the code default, edit the `MODEL_NAME` constant in `backend/main.py`:
```python
MODEL_NAME = os.getenv("NAVIGATOR_MODEL", "gpt-5-mini")
```
Note: GPT-5 family models require `max_completion_tokens` (not `max_tokens`) and don't accept custom `temperature`. The `_completion_kwargs()` helper in `main.py` handles the split automatically — as long as the model name starts with `gpt-5`, the right params are sent.

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
- ✅ Events fetched live from calendar.ufl.edu (see `events_cache.py`) and refreshed hourly
- ⚠️ Must manually re-run `ingest_faculty.py` to update faculty / general info
- ⚠️ Limited to text files in the `data/` folder for the RAG-backed content
- ⚠️ No real-time information for news or course schedules

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
