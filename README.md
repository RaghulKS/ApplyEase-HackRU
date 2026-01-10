# ApplyEase - AI-Powered Application Assistant

ApplyEase is an intelligent Chrome extension that automates internship and job applications using AI. It combines machine learning for field detection, LangChain-powered chatbot assistance, and automatic application tracking via Google Sheets.

## Features

- ** Smart Form Detection**: ML-powered classification of form fields (standard vs. unique)
- ** AI Response Generation**: Gemini AI generates contextual responses for application questions
- ** Auto-Fill**: Automatically fills standard fields from your saved profile
- ** Application Tracking**: Logs all applications to Google Sheets automatically
- ** Interactive Chat Assistant**: Get real-time help with difficult application questions
- ** Smart Response Memory**: Learns from your edits to improve future suggestions
- ** Secure Authentication**: JWT-based auth system to protect your data

##  System Architecture

```
┤ Chrome Extension (Frontend)
├── Content Scripts: Form detection and filling
├── Background Script: API communication
├── Popup UI: User dashboard
└── Side Panel: AI chat interface

┤ FastAPI Backend
├── ML Field Classifier (Sentence-BERT)
├── Resume Parser (PyPDF2 + spaCy)
├── Chatbot Service (LangChain + Gemini)
├── Google Sheets Tracker
└── SQLite Database
```

## Tech Stack

### Backend
- **FastAPI**: High-performance API framework
- **LangChain**: LLM orchestration
- **Sentence-Transformers**: Field classification
- **Google Gemini AI**: Response generation
- **spaCy**: NLP and resume parsing
- **SQLAlchemy**: ORM for database
- **Google Sheets API**: Application tracking

### Chrome Extension
- **Vanilla JavaScript**: Content scripts
- **Chrome Extension Manifest V3**: Latest extension standard
- **HTML/CSS**: Popup and panel UI

## Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **Google Chrome** browser
3. **API Keys**:
   - Google Gemini API key ([Get it here](https://makersuite.google.com/app/apikey))
   - Google Sheets API credentials ([Setup guide](https://developers.google.com/sheets/api/quickstart/python))

### Step 1: Clone and Setup Backend

```bash
# Clone the repository (or navigate to the applyease folder)
cd applyease

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### Step 2: Configure Environment

1. Copy `env.example` to `.env` in the applyease folder:
```bash
cp env.example .env
```

2. Edit `.env` and add your API keys:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
SECRET_KEY=generate_a_random_secret_key_here
```

3. For Google Sheets:
   - Create a new Google Cloud project
   - Enable Google Sheets API
   - Create service account credentials
   - Download JSON credentials and save as `credentials.json` in the backend folder
   - Create a new Google Sheet and share it with the service account email

### Step 3: Start the Backend Server

```bash
# From the backend directory
python -m app.main

# Or use uvicorn directly
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

### Step 4: Load Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `applyease/extension` folder
5. The ApplyEase extension icon should appear in your toolbar

### Step 5: Create Your Account

1. Click the ApplyEase extension icon
2. Click "Create New Account"
3. Register with your email and password
4. Upload your resume (PDF format)
5. Fill in your profile details

## Usage Guide

### Basic Workflow

1. **Navigate to a job application page** (LinkedIn, Greenhouse, Lever, etc.)
2. **Click the ApplyEase floating button** (purple button in bottom-right)
3. **Review detected fields** in the side panel
4. **Click "Auto-Fill Form"** to fill all fields
5. **Review AI-generated responses** for unique questions
6. **Edit if needed** and submit your application
7. **Application automatically logged** to your Google Sheet

### Features in Detail

#### Field Detection
- Automatically identifies all form fields on the page
- Classifies as "standard" (auto-fillable) or "unique" (needs AI)
- Shows confidence scores for each classification

#### AI Assistant Chat
- Ask questions about specific fields
- Get suggestions for improving responses
- Request different variations of answers
- Learn company-specific tips

#### Application Tracker
- Automatic logging to Google Sheets
- Tracks: Company, Position, Date, Status, URL
- Export to CSV for analysis
- Dashboard with statistics

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create new account
- `POST /api/auth/login` - Login and get token
- `GET /api/auth/me` - Get current user info

### Profile Management
- `GET /api/profile` - Get user profile
- `PUT /api/profile` - Update profile

### Resume
- `POST /api/resume/upload` - Upload and parse resume
- `GET /api/resume` - List all resumes
- `GET /api/resume/primary` - Get primary resume

### Applications
- `POST /api/applications` - Save new application
- `GET /api/applications` - List applications with filters
- `PUT /api/applications/{id}` - Update application status
- `GET /api/applications/stats/summary` - Get statistics

### Field Detection
- `POST /api/fields/detect` - Classify form fields
- `POST /api/fields/validate` - Validate field values

### Chatbot
- `POST /api/chatbot/generate` - Generate AI response
- `POST /api/chatbot/save-response` - Save successful response
- `GET /api/chatbot/saved-responses` - Get saved responses
- `POST /api/chatbot/learn` - Learn from user edits

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini AI API key | Yes |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | Path to Google service account JSON | Yes |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | ID of your tracking spreadsheet | Yes |
| `SECRET_KEY` | JWT secret key for authentication | Yes |
| `DATABASE_URL` | SQLite database path | No |
| `API_HOST` | Backend host (default: 127.0.0.1) | No |
| `API_PORT` | Backend port (default: 8000) | No |

### Chrome Extension Settings

Edit `extension/src/background/background.js` to change:
- `API_URL`: Backend server URL (default: `http://localhost:8000`)

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/

# With coverage
pytest --cov=app tests/
```

### Database Migrations

```bash
# Initialize database
python -c "from app.models.database import init_db; init_db()"
```

### Training ML Model

```bash
# Train field classifier with custom data
python -m app.ml.train_classifier --data path/to/training_data.json
```

## Troubleshooting

### Common Issues

1. **"CORS error" in Chrome extension**
   - Ensure backend is running on `http://localhost:8000`
   - Check that CORS middleware is properly configured

2. **"Authentication failed"**
   - Verify JWT secret key is set in `.env`
   - Check token expiration settings

3. **"Google Sheets not updating"**
   - Verify service account has edit access to the sheet
   - Check credentials.json is in correct location

4. **"AI responses are generic"**
   - Ensure Gemini API key is valid
   - Upload a detailed resume for better context
   - Add more information to your profile

5. **"Fields not detected on some sites"**
   - Some sites use shadow DOM or iframes
   - Try refreshing the page after it fully loads
   - Report the site for improvement

### Debug Mode

1. **Backend Debug**:
```bash
uvicorn app.main:app --reload --log-level debug
```

2. **Extension Debug**:
- Open Chrome DevTools on any tab
- Go to "Sources" > "Content Scripts"
- Set breakpoints in content.js

## Security Considerations

1. **Never commit `.env` file or API keys**
2. **Use strong SECRET_KEY for JWT**
3. **Keep Google Sheets credentials secure**
4. **Don't share your Gemini API key**
5. **Use HTTPS in production**

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - feel free to use this project for personal or commercial purposes.


