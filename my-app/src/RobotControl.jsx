import { useState, useEffect } from 'react';
import { supabase } from './dbconnect';

function Verification({ session }) {
  const [photos, setPhotos] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [robotCommands, setRobotCommands] = useState([]);
  const [audioRecording, setAudioRecording] = useState(false);
  const [textCommand, setTextCommand] = useState('');
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (session?.user) {
      fetchPhotos();
      fetchRobotCommands();
    }
  }, [session]);

  const fetchPhotos = async () => {
    try {
      const { data, error } = await supabase
        .from('photos')
        .select('*')
        .order('upload_time', { ascending: false });

      if (error) throw error;
      setPhotos(data || []);
    } catch (error) {
      console.error('Error fetching photos:', error);
    }
  };

  const fetchRobotCommands = async () => {
    try {
      const { data, error } = await supabase
        .from('user_profiles')
        .select('*')
        .eq('is_command', true)
        .order('id', { ascending: false });

      if (error) throw error;
      setRobotCommands(data || []);
    } catch (error) {
      console.error('Error fetching commands:', error);
    }
  };

  const uploadPhoto = async (event) => {
    try {
      setUploading(true);
      const files = event.target.files;
      
      if (!files || files.length === 0) return;

      for (const file of Array.from(files).slice(0, 3)) { // Limit to 3 files
        const fileExt = file.name.split('.').pop();
        const fileName = `${Date.now()}_${Math.random().toString(36).substring(2)}.${fileExt}`;
        const filePath = `${session.user.id}/${fileName}`;

        console.log('Uploading file:', filePath);

        // Upload to storage bucket
        const { error: uploadError } = await supabase.storage
          .from('images')
          .upload(filePath, file);

        if (uploadError) throw uploadError;

        // Save metadata to photos table (user_id auto-filled by auth.uid())
        const { error: dbError } = await supabase
          .from('photos')
          .insert({
            storage_path: filePath,
            filename: file.name
          });

        if (dbError) throw dbError;

        console.log('Photo uploaded successfully:', fileName);
      }

      // Refresh photos list
      await fetchPhotos();
      event.target.value = ''; // Clear file input
      
    } catch (error) {
      console.error('Upload error:', error);
      alert(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const sendTextCommand = async () => {
    if (!textCommand.trim()) return;

    setProcessing(true);
    try {
      console.log('Sending text command:', textCommand);

      // Send to your Flask backend for AI processing
      const response = await fetch('/api/process-text-command', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: textCommand,
          user_id: session.user.id
        }),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const result = await response.json();
      console.log('AI processing result:', result);

      // Save to database using your current structure - matches main_processor.py output
      const { error } = await supabase
        .from('user_profiles')
        .insert({
          action: result.action_number,          // From main_processor.py
          response: result.voice_response,       // From main_processor.py  
          is_command: result.command_type === 'command'
        });

      if (error) throw error;

      // Clear input and refresh commands
      setTextCommand('');
      await fetchRobotCommands();
      
    } catch (error) {
      console.error('Command processing error:', error);
      alert(`Command failed: ${error.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const recordAudio = async () => {
    try {
      setAudioRecording(true);
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const chunks = [];

      mediaRecorder.ondataavailable = (event) => {
        chunks.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: 'audio/wav' });
        await sendAudioCommand(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();

      // Stop recording after 5 seconds
      setTimeout(() => {
        mediaRecorder.stop();
        setAudioRecording(false);
      }, 5000);

    } catch (error) {
      console.error('Audio recording error:', error);
      alert(`Recording failed: ${error.message}`);
      setAudioRecording(false);
    }
  };

  const sendAudioCommand = async (audioBlob) => {
    setProcessing(true);
    try {
      console.log('Sending audio command...');

      const formData = new FormData();
      formData.append('audio', audioBlob, 'command.wav');
      formData.append('user_id', session.user.id);

      // Send to your Flask backend for AI processing using main_processor.py
      const response = await fetch('/api/upload-audio', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const result = await response.json();
      console.log('Audio processing result:', result);

      // Save to database - matches main_processor.py output format
      const { error } = await supabase
        .from('user_profiles')
        .insert({
          action: result.action_number,          // From main_processor.py
          response: result.voice_response,       // From main_processor.py
          is_command: result.command_type === 'command'
        });

      if (error) throw error;

      // Refresh commands
      await fetchRobotCommands();
      
    } catch (error) {
      console.error('Audio command error:', error);
      alert(`Audio command failed: ${error.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const deletePhoto = async (photo) => {
    try {
      // Delete from storage
      const { error: storageError } = await supabase.storage
        .from('images')
        .remove([photo.storage_path]);

      if (storageError) throw storageError;

      // Delete from database
      const { error: dbError } = await supabase
        .from('photos')
        .delete()
        .eq('id', photo.id);

      if (dbError) throw dbError;

      // Refresh photos
      await fetchPhotos();
      
    } catch (error) {
      console.error('Delete error:', error);
      alert(`Delete failed: ${error.message}`);
    }
  };

  const getImageUrl = (photo) => {
    const { data } = supabase.storage
      .from('images')
      .getPublicUrl(photo.storage_path);
    return data.publicUrl;
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <h2>🤖 Robot Pet Dashboard</h2>
        <div>
          <span>Welcome, {session?.user?.email}</span>
          <button 
            onClick={() => supabase.auth.signOut()}
            style={{ marginLeft: '10px', padding: '8px 16px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Photo Upload Section */}
      <div style={{ marginBottom: '40px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
        <h3>📸 Photo Upload (for future CV programs)</h3>
        <div style={{ marginBottom: '20px' }}>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={uploadPhoto}
            disabled={uploading}
            style={{ marginRight: '10px' }}
          />
          <span style={{ fontSize: '14px', color: '#666' }}>
            {uploading ? 'Uploading...' : 'Select up to 3 images'}
          </span>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '15px' }}>
          {photos.map((photo) => (
            <div key={photo.id} style={{ border: '1px solid #ddd', borderRadius: '8px', overflow: 'hidden' }}>
              <img 
                src={getImageUrl(photo)}
                alt={photo.filename}
                style={{ width: '100%', height: '150px', objectFit: 'cover' }}
              />
              <div style={{ padding: '10px' }}>
                <p style={{ margin: '0', fontSize: '12px', fontWeight: 'bold' }}>{photo.filename}</p>
                <p style={{ margin: '5px 0 0 0', fontSize: '10px', color: '#666' }}>
                  {new Date(photo.upload_time).toLocaleDateString()}
                </p>
                <button
                  onClick={() => deletePhoto(photo)}
                  style={{ marginTop: '5px', padding: '4px 8px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', fontSize: '10px' }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
        {photos.length === 0 && !uploading && (
          <p style={{ color: '#666', fontStyle: 'italic' }}>No images uploaded yet. Upload some photos for your future CV programs!</p>
        )}
      </div>

      {/* Robot Control Section */}
      <div style={{ marginBottom: '40px', padding: '20px', backgroundColor: '#e7f3ff', borderRadius: '8px' }}>
        <h3>🎤 Robot Voice Commands</h3>
        
        {/* Text Input */}
        <div style={{ marginBottom: '20px' }}>
          <input
            type="text"
            value={textCommand}
            onChange={(e) => setTextCommand(e.target.value)}
            placeholder="Type a command like 'go forward' or 'turn left'"
            disabled={processing}
            style={{ width: '300px', padding: '10px', marginRight: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
            onKeyPress={(e) => e.key === 'Enter' && sendTextCommand()}
          />
          <button
            onClick={sendTextCommand}
            disabled={processing || !textCommand.trim()}
            style={{ padding: '10px 20px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            {processing ? 'Processing...' : 'Send Command'}
          </button>
        </div>

        {/* Audio Recording */}
        <div style={{ marginBottom: '20px' }}>
          <button
            onClick={recordAudio}
            disabled={audioRecording || processing}
            style={{ 
              padding: '15px 25px', 
              backgroundColor: audioRecording ? '#ffc107' : '#007bff', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              fontSize: '16px'
            }}
          >
            {audioRecording ? '🔴 Recording... (5s)' : '🎤 Record Voice Command'}
          </button>
        </div>

        {/* Status */}
        {processing && (
          <div style={{ padding: '10px', backgroundColor: '#fff3cd', border: '1px solid #ffeaa7', borderRadius: '4px', marginBottom: '20px' }}>
            🤖 Processing your command with AI...
          </div>
        )}
      </div>

      {/* Command History */}
      <div style={{ padding: '20px', backgroundColor: '#f0f8f0', borderRadius: '8px' }}>
        <h3>📋 Recent Commands</h3>
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {robotCommands.length === 0 ? (
            <p style={{ color: '#666', fontStyle: 'italic' }}>No commands yet. Try saying "go forward" or "turn left"!</p>
          ) : (
            robotCommands.map((cmd) => {
              const actionNames = ['stay still', 'move forward', 'move backward', 'turn left', 'turn right'];
              const actionName = actionNames[cmd.action] || 'unknown action';
              
              return (
                <div key={cmd.id} style={{ 
                  padding: '15px', 
                  marginBottom: '10px', 
                  backgroundColor: 'white', 
                  border: '1px solid #ddd', 
                  borderRadius: '6px',
                  borderLeft: `4px solid ${cmd.is_command ? '#28a745' : '#007bff'}`
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
                        🤖 Action #{cmd.action}: {actionName}
                      </div>
                      <div style={{ color: '#666', fontSize: '14px' }}>
                        "{cmd.response}"
                      </div>
                    </div>
                    <span style={{ 
                      fontSize: '12px', 
                      color: '#666',
                      backgroundColor: cmd.is_command ? '#d4edda' : '#d1ecf1',
                      padding: '2px 6px',
                      borderRadius: '3px'
                    }}>
                      {cmd.is_command ? 'Command' : 'Chat'}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

export default Verification;