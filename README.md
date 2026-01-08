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
