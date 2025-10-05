# 🤖 AI Robot Pet - Setup Instructions

## Environment Configuration

### Required API Keys & Configuration

You need to update the following files with your actual API keys:

#### 1. Backend Configuration (`my-app/src/backend/.env`)

```bash
# Supabase Configuration - Online Database
SUPABASE_URL=https://proavqhzzoljnoeomddd.supabase.co  # ✅ Already configured
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # ✅ Already configured

# 🔑 TODO: Add your Supabase Service Role Key
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# 🔑 TODO: Add your Google Gemini API Key  
GEMINI_API_KEY=AIzaSy...
```

#### 2. Frontend Configuration (`my-app/.env`)
```bash
# ✅ Already configured correctly
VITE_SUPABASE_URL="https://proavqhzzoljnoeomddd.supabase.co"
VITE_SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Where to Get API Keys

#### Supabase Service Role Key
1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project: `proavqhzzoljnoeomddd`
3. Go to **Settings** > **API**
4. Copy the **service_role** secret key (not the anon public key)
5. Paste it in your backend `.env` file

#### Google Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key or use an existing one
3. Copy the API key (starts with `AIzaSy...`)
4. Paste it in your backend `.env` file

### Database Setup

#### Run the Database Schema
1. Go to your [Supabase Dashboard](https://supabase.com/dashboard)
2. Navigate to your project
3. Go to **SQL Editor**
4. Copy the contents of `my-app/src/backend/database_schema.sql`
5. Paste and run it to create all required tables

### Architecture Overview

```
React Frontend (my-app/src/)
    ↓ API calls
Flask Backend (my-app/src/backend/app.py)
    ↓ Database queries
Supabase Online Database (proavqhzzoljnoeomddd.supabase.co)
    ↓ Command polling
Raspberry Pi Client (pi_client.py)
    ↓ Physical actions
Robot Hardware
```

### Starting the System

#### 1. Install Backend Dependencies
```bash
cd my-app/src/backend
pip install -r requirements.txt
```

#### 2. Start Backend Server
```bash
cd my-app/src/backend
python app.py
# Server runs on http://localhost:5000
```

#### 3. Start Frontend Development Server
```bash
cd my-app
npm install
npm run dev
# Frontend runs on http://localhost:5173
```

#### 4. Setup Raspberry Pi (Optional)
```bash
# On Raspberry Pi
cd my-app/src/backend
python pi_client.py
# Pi polls Supabase database for commands
```

### API Endpoints

The unified backend (`app.py`) provides:

- **Image Upload**: `POST /images`
- **Robot Commands**: `POST /api/upload-audio`
- **Command History**: `GET /api/history`
- **Health Check**: `GET /health`
- **Server Status**: `GET /api/status`

### Database Tables

Your Supabase database will have:

- `photos` - Image upload metadata
- `robot_commands` - Voice commands and AI responses
- `command_history` - Execution logs
- `user_profiles` - User preferences
- `audio_files` - Audio file metadata

### Security Features

- ✅ Row Level Security (RLS) enabled
- ✅ User authentication required
- ✅ CORS properly configured
- ✅ Service role for Pi client access

### Next Steps

1. **Add your API keys** to the backend `.env` file
2. **Run the database schema** in Supabase SQL editor
3. **Start both servers** (backend and frontend)
4. **Test the integration** by uploading images and sending voice commands

### Troubleshooting

- **Backend won't start**: Check your API keys in `.env`
- **Database errors**: Ensure you've run the schema SQL
- **CORS issues**: Check ALLOWED_ORIGINS in backend `.env`
- **Pi client issues**: Verify Supabase service role key

---

🚀 **Your system is configured to use online Supabase database only - no local database files!**