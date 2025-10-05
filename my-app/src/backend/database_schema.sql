-- AI Robot Pet Database Schema
-- Run these SQL commands in your Supabase SQL editor

-- Enable RLS (Row Level Security) for all tables
SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';

-- ======================
-- TABLES CREATION
-- ======================

-- 1. Photos table (for image uploads)
CREATE TABLE IF NOT EXISTS public.photos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    filename TEXT,
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    file_size INTEGER,
    content_type TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Robot Commands table (for voice commands and AI processing)
CREATE TABLE IF NOT EXISTS public.robot_commands (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    transcription TEXT NOT NULL,
    action_number INTEGER NOT NULL CHECK (action_number >= 0 AND action_number <= 4),
    voice_response TEXT NOT NULL,
    command_type TEXT NOT NULL CHECK (command_type IN ('command', 'conversation')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    audio_file_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Command History table (for tracking all interactions)
CREATE TABLE IF NOT EXISTS public.command_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    command_id UUID REFERENCES public.robot_commands(id) ON DELETE CASCADE,
    action_taken TEXT NOT NULL,
    execution_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    success BOOLEAN DEFAULT TRUE,
    pi_response TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. User Profiles table (extended user information)
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    robot_name TEXT DEFAULT 'Robot Pet',
    preferences JSONB DEFAULT '{}',
    total_commands INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Audio Files table (for storing audio metadata)
CREATE TABLE IF NOT EXISTS public.audio_files (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    command_id UUID REFERENCES public.robot_commands(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    duration_seconds DECIMAL(10,2),
    format TEXT,
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ======================
-- INDEXES FOR PERFORMANCE
-- ======================

-- Photos indexes
CREATE INDEX IF NOT EXISTS idx_photos_user_id ON public.photos(user_id);
CREATE INDEX IF NOT EXISTS idx_photos_upload_time ON public.photos(upload_time DESC);

-- Robot Commands indexes
CREATE INDEX IF NOT EXISTS idx_robot_commands_user_id ON public.robot_commands(user_id);
CREATE INDEX IF NOT EXISTS idx_robot_commands_status ON public.robot_commands(status);
CREATE INDEX IF NOT EXISTS idx_robot_commands_timestamp ON public.robot_commands(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_robot_commands_action_number ON public.robot_commands(action_number);

-- Command History indexes
CREATE INDEX IF NOT EXISTS idx_command_history_user_id ON public.command_history(user_id);
CREATE INDEX IF NOT EXISTS idx_command_history_command_id ON public.command_history(command_id);
CREATE INDEX IF NOT EXISTS idx_command_history_execution_time ON public.command_history(execution_time DESC);

-- User Profiles indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON public.user_profiles(user_id);

-- Audio Files indexes
CREATE INDEX IF NOT EXISTS idx_audio_files_command_id ON public.audio_files(command_id);
CREATE INDEX IF NOT EXISTS idx_audio_files_user_id ON public.audio_files(user_id);

-- ======================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ======================

-- Enable RLS on all tables
ALTER TABLE public.photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.robot_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.command_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audio_files ENABLE ROW LEVEL SECURITY;

-- Photos policies
CREATE POLICY "Users can view own photos" ON public.photos
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own photos" ON public.photos
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own photos" ON public.photos
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own photos" ON public.photos
    FOR DELETE USING (auth.uid() = user_id);

-- Robot Commands policies
CREATE POLICY "Users can view own commands" ON public.robot_commands
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own commands" ON public.robot_commands
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own commands" ON public.robot_commands
    FOR UPDATE USING (auth.uid() = user_id);

-- Special policy for service role to update command status (for Pi client)
CREATE POLICY "Service role can update command status" ON public.robot_commands
    FOR UPDATE USING (auth.jwt() ->> 'role' = 'service_role');

-- Command History policies
CREATE POLICY "Users can view own command history" ON public.command_history
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own command history" ON public.command_history
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- User Profiles policies
CREATE POLICY "Users can view own profile" ON public.user_profiles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile" ON public.user_profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own profile" ON public.user_profiles
    FOR UPDATE USING (auth.uid() = user_id);

-- Audio Files policies
CREATE POLICY "Users can view own audio files" ON public.audio_files
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own audio files" ON public.audio_files
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- ======================
-- FUNCTIONS AND TRIGGERS
-- ======================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at columns
DROP TRIGGER IF EXISTS update_robot_commands_updated_at ON public.robot_commands;
CREATE TRIGGER update_robot_commands_updated_at
    BEFORE UPDATE ON public.robot_commands
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON public.user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to auto-create user profile
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id, display_name)
    VALUES (NEW.id, NEW.raw_user_meta_data->>'display_name');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile when user signs up
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ======================
-- STORAGE BUCKET SETUP
-- ======================

-- Create storage bucket for images (run in Supabase dashboard if needed)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('images', 'images', true);

-- Storage policies for images bucket
-- CREATE POLICY "Users can upload images" ON storage.objects
--     FOR INSERT WITH CHECK (bucket_id = 'images' AND auth.role() = 'authenticated');

-- CREATE POLICY "Images are publicly accessible" ON storage.objects
--     FOR SELECT USING (bucket_id = 'images');

-- ======================
-- SAMPLE DATA (OPTIONAL)
-- ======================

-- Insert sample action mappings for reference
COMMENT ON TABLE public.robot_commands IS 'Action mappings: 0=do nothing, 1=forward, 2=backward, 3=left, 4=right';

-- ======================
-- VIEWS FOR ANALYTICS (OPTIONAL)
-- ======================

-- View for command statistics
CREATE OR REPLACE VIEW public.command_stats AS
SELECT 
    user_id,
    COUNT(*) as total_commands,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_commands,
    COUNT(CASE WHEN command_type = 'command' THEN 1 END) as movement_commands,
    COUNT(CASE WHEN command_type = 'conversation' THEN 1 END) as conversations,
    MAX(timestamp) as last_command_time
FROM public.robot_commands 
GROUP BY user_id;

-- Grant access to views
GRANT SELECT ON public.command_stats TO authenticated;

-- ======================
-- COMPLETION MESSAGE
-- ======================

DO $$
BEGIN
    RAISE NOTICE 'AI Robot Pet database schema created successfully!';
    RAISE NOTICE 'Tables created: photos, robot_commands, command_history, user_profiles, audio_files';
    RAISE NOTICE 'RLS policies enabled for security';
    RAISE NOTICE 'Indexes created for performance';
    RAISE NOTICE 'Ready for React frontend and Flask backend integration!';
END $$;