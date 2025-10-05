# 🧪 AI Robot Pet - Complete Testing Guide

## Prerequisites Setup

### 1. Configure API Keys
First, add your actual API keys to the backend environment file:

```bash
# Edit: my-app/src/backend/.env
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Get from Supabase Dashboard
GEMINI_API_KEY=AIzaSy...  # Get from Google AI Studio
```

### 2. Setup Database Schema
1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Open your project: `proavqhzzoljnoeomddd`
3. Go to **SQL Editor**
4. Copy contents of `my-app/src/backend/database_schema.sql`
5. Paste and **Run** to create all tables

### 3. Install Dependencies
```bash
# Backend dependencies
cd my-app/src/backend
pip install -r requirements.txt

# Frontend dependencies  
cd my-app
npm install
```

---

## 🚀 Step-by-Step Testing

### Test 1: Backend Server Health Check

```bash
# Start the unified Flask backend
cd my-app/src/backend
python app.py
```

**Expected Output:**
```
🚀 Starting Unified AI Robot Pet Backend...
📁 Upload folder: uploads
✅ Supabase connected successfully
🔗 Database URL: https://proavqhzzoljnoeomddd.supabase.co
✅ Database tables accessible
🤖 Robot AI Processor initialized
🌐 Server starting on http://0.0.0.0:5000
```

**Test the health endpoint:**
```bash
curl http://localhost:5000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-05T...",
  "supabase": "connected",
  "robot_ai": "ready"
}
```

### Test 2: Frontend Development Server

```bash
# In a new terminal
cd my-app
npm run dev
```

**Expected Output:**
```
VITE v5.x.x ready in xxx ms
➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

**Open browser:** http://localhost:5173

### Test 3: User Authentication Flow

1. **Navigate to:** http://localhost:5173
2. **Should redirect to:** `/login`
3. **Sign up/Login** with email and password
4. **Should redirect to:** `/verification` after successful auth
5. **Check Supabase Dashboard → Authentication → Users** - should see your user

### Test 4: Image Upload Functionality

On the verification page:
1. **Click** "Choose Files" button
2. **Select** 1-3 image files (JPG, PNG, etc.)
3. **Click** "Upload Photos"
4. **Expected result:** Success message with uploaded URLs

**Verify in Supabase:**
- Go to **Storage → images bucket** - should see uploaded files
- Go to **Table Editor → photos** - should see metadata records

### Test 5: Robot Voice Commands (Core Feature)

This is the main AI robot functionality test:

#### 5a. Test Audio Upload API (Backend)
```bash
# Create a test audio file or use existing
curl -X POST http://localhost:5000/api/upload-audio \
  -H "x-user-id: test-user" \
  -F "audio=@path/to/your/audio/file.wav"
```

**Expected Response:**
```json
{
  "success": true,
  "result": {
    "transcription": "go forward",
    "action_number": 1,
    "voice_response": "Moving forward now.",
    "command_type": "command"
  },
  "command_id": "uuid-here"
}
```

#### 5b. Test Text Input (Alternative)
You can test the AI processing without audio:
```bash
# Test the main processor directly
cd my-app/src/backend
python -c "
from main_processor import MainRobotProcessor
processor = MainRobotProcessor()
result = processor.process_text_command('turn left please')
print(result)
"
```

### Test 6: Database Integration

Check if commands are being saved to Supabase:

1. **Supabase Dashboard → Table Editor → robot_commands**
2. Should see records with:
   - `transcription`: What user said
   - `action_number`: 0-4 robot action
   - `status`: "pending"
   - `voice_response`: AI response
   - `user_id`: Your authenticated user ID

### Test 7: Command History API

```bash
curl "http://localhost:5000/api/history?user_id=test-user&limit=5"
```

**Expected Response:**
```json
{
  "history": [
    {
      "id": "uuid",
      "transcription": "go forward", 
      "action_number": 1,
      "status": "pending",
      "timestamp": "2025-10-05T..."
    }
  ],
  "source": "supabase_database"
}
```

### Test 8: Pi Client Database Polling

```bash
# Test Pi client (simulates Raspberry Pi)
cd my-app/src/backend
python pi_client.py
```

**Expected Output:**
```
🤖 Pi Robot Client initialized
🌐 Supabase: https://proavqhzzoljnoeomddd.supabase.co
✅ Database connection test successful
🔄 Polling every 2.0 seconds...
📋 Found X pending commands
🎯 Executing action 1
➡️  MOVE FORWARD
✅ Command completed: uuid
```

---

## 🔄 Complete End-to-End Test Flow

### Full System Integration Test:

1. **Start both servers** (backend + frontend)
2. **Login** to frontend
3. **Record audio** saying: "move forward please"
4. **Upload audio** via frontend (you'll need to build this component)
5. **Check database** - should see new robot_command with status "pending"
6. **Start Pi client** - should pick up and "execute" the command
7. **Check database** - status should update to "completed"
8. **View history** - should show the complete interaction

---

## 🧪 Testing Each Component Individually

### Backend API Endpoints Testing

```bash
# Health check
curl http://localhost:5000/health

# Server status
curl http://localhost:5000/api/status

# Upload audio (replace with actual file)
curl -X POST http://localhost:5000/api/upload-audio \
  -H "x-user-id: your-user-id" \
  -F "audio=@test.wav"

# Get command history
curl "http://localhost:5000/api/history?user_id=your-user-id"

# Get pending commands (what Pi client sees)
curl http://localhost:5000/api/commands/pending

# Update command status (what Pi client does)
curl -X PUT http://localhost:5000/api/commands/YOUR-COMMAND-ID/status \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'
```

### Database Direct Testing

In Supabase SQL Editor:
```sql
-- Check all tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

-- Check robot commands
SELECT * FROM robot_commands ORDER BY timestamp DESC LIMIT 5;

-- Check command history
SELECT * FROM command_history ORDER BY execution_time DESC LIMIT 5;

-- Check user profiles
SELECT * FROM user_profiles;
```

---

## 🐛 Troubleshooting Guide

### Common Issues & Solutions:

#### "Supabase not configured"
- ✅ Add `SUPABASE_SERVICE_ROLE_KEY` to backend `.env`
- ✅ Verify URL matches your project

#### "Robot AI Processor failed"
- ✅ Add `GEMINI_API_KEY` to backend `.env`
- ✅ Check Google AI Studio quota

#### "Database tables not accessible"
- ✅ Run the `database_schema.sql` in Supabase SQL editor
- ✅ Check RLS policies allow your operations

#### "CORS errors"
- ✅ Verify `ALLOWED_ORIGINS` includes your frontend URL
- ✅ Check Vite proxy configuration

#### "Pi client can't connect"
- ✅ Ensure service role key has proper permissions
- ✅ Check network connectivity to Supabase

---

## 🎯 Success Criteria

Your system is working correctly if:

- ✅ **Frontend loads** and authentication works
- ✅ **Backend connects** to Supabase successfully  
- ✅ **Image uploads** work and appear in storage
- ✅ **Voice commands** are processed by AI correctly
- ✅ **Commands are saved** to database with correct status
- ✅ **Pi client polls** and updates command status
- ✅ **Command history** shows complete interaction logs
- ✅ **All APIs respond** with expected JSON structures

---

## 📊 Monitoring Your System

### Key Metrics to Watch:
- **Backend logs**: Connection status, API responses
- **Supabase Dashboard**: Table contents, storage usage
- **Browser Network tab**: API call success/failure
- **Pi client output**: Command execution status

Your AI Robot Pet system integrates React frontend, Flask backend, Supabase database, and Pi client - test each layer to ensure seamless operation! 🤖✨