# UF Water Institute Faculty Chatbot

A RAG-powered chatbot that answers questions about UF Water Institute faculty members using GPT-4o and ChromaDB.

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

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-...your_key_here
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

## Deploying to Production

### Backend Deployment (Render/Railway)

1. **Create a `Dockerfile`** (optional but recommended):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
COPY data/ ../data/
COPY chroma/ ../chroma/
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Deploy to Render/Railway**:
   - Push your code to GitHub
   - Connect to Render.com or Railway.app
   - Set environment variable: `OPENAI_API_KEY`
   - Deploy!

3. **After deployment**, run the ingestion script once:
```bash
python ingest_faculty.py
```

### Frontend Deployment

#### Option 1: WordPress Iframe Embed (Recommended - Most Stable)

1. Host `frontend/index.html` on any static host (Netlify, Vercel, GitHub Pages)
2. Update `API_URL` in `index.html` to your deployed backend URL
3. In WordPress, add this to your page:

```html
<iframe
  src="https://your-frontend-url.com"
  width="100%"
  height="650px"
  frameborder="0"
  style="border: none; border-radius: 12px;"
></iframe>
```

#### Option 2: Direct WordPress Page Embed

1. Update `API_URL` in the frontend HTML
2. Copy the entire HTML content
3. In WordPress, edit your page in "Code" or "HTML" mode
4. Paste the HTML directly

## Architecture

- **Backend**: FastAPI + ChromaDB for vector search
- **Frontend**: Vanilla HTML/CSS/JS (no dependencies)
- **AI Model**: GPT-4o (adjustable in `main.py`)
- **Vector DB**: ChromaDB (persistent storage in `chroma/db/`)

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
