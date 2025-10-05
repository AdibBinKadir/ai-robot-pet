import { useState, useRef, useEffect } from "react";
import { DeviceCard } from "./components/DeviceCard.jsx";
import { Mic, MicOff } from "lucide-react";
import { supabase } from './dbconnect';
import './styles/mic.css'

export default function Microphone() {
  const [devices, setDevices] = useState([
    {
      id: "1",
      name: "PetPal",
      type: "laptop",
      status: "available",
    },
  ]);

  const [isMicOn, setIsMicOn] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastResponse, setLastResponse] = useState('');
  const [user, setUser] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const hasConnectedDevice = devices.some(
    (device) => device.status === "connected"
  );

  useEffect(() => {
    // Get current user session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const toggleDevice = (id) => {
    setDevices((prev) =>
      prev.map((device) =>
        device.id === id
          ? {
              ...device,
              status: device.status === "connected" ? "available" : "connected",
            }
          : device
      )
    );
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        } 
      });
      
      // Try to use the best supported format
      let options = {};
      if (MediaRecorder.isTypeSupported('audio/mp4')) {
        options.mimeType = 'audio/mp4';
      } else if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        options.mimeType = 'audio/webm;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/webm')) {
        options.mimeType = 'audio/webm';
      }
      
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      
      audioChunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await processAudioFile(audioBlob);
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorderRef.current.start(1000); // Collect data every second
      setIsRecording(true);
      
    } catch (error) {
      console.error('❌ Failed to start recording:', error);
      alert('Failed to access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processAudioFile = async (audioBlob) => {
    if (!user) {
      alert('Please login to process audio');
      return;
    }

    setIsProcessing(true);
    
    try {
      // Convert WebM to WAV for better compatibility
      const audioBuffer = await audioBlob.arrayBuffer();
      const wavBlob = new Blob([audioBuffer], { type: 'audio/wav' });
      
      // Create FormData to send audio file
      const formData = new FormData();
      formData.append('audio', wavBlob, 'recording.wav');
      
      // Send to backend for processing
      const response = await fetch('http://localhost:5000/api/upload-audio', {
        method: 'POST',
        headers: {
          'x-user-id': user.id
        },
        body: formData
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const result = await response.json();
      
      if (result.success) {
        // Update user profile with the processed data
        await updateUserProfile(result.result);
        
        setLastResponse(result.result.voice_response);
      } else {
        throw new Error(result.error || 'Processing failed');
      }
      
    } catch (error) {
      console.error('❌ Audio processing failed:', error);
      alert(`Processing failed: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const updateUserProfile = async (aiResult) => {
    try {
      // Check if user already has a profile (without .single() to avoid errors)
      const { data: existingProfiles, error: selectError } = await supabase
        .from('user_profiles')
        .select('id')
        .eq('user_id', user.id);

      if (selectError) {
        throw selectError;
      }

      const profileData = {
        action: aiResult.action_number,
        response: aiResult.voice_response,
        is_command: aiResult.command_type === 'command'
      };

      if (existingProfiles && existingProfiles.length > 0) {
        // User already has a profile - UPDATE it
        const { error: updateError } = await supabase
          .from('user_profiles')
          .update(profileData)
          .eq('user_id', user.id);
          
        if (updateError) {
          throw updateError;
        }
      } else {
        // User doesn't have a profile - INSERT new one
        const { error: insertError } = await supabase
          .from('user_profiles')
          .insert({
            user_id: user.id,
            ...profileData
          });
          
        if (insertError) {
          throw insertError;
        }
      }
      
    } catch (error) {
      console.error('❌ Failed to update user profile:', error);
      alert(`❌ Database error: ${error.message}`);
    }
  };



  const handleMicrophoneToggle = () => {
    if (!hasConnectedDevice) return;
    
    if (isRecording) {
      stopRecording();
      setIsMicOn(false);
    } else {
      startRecording();
      setIsMicOn(true);
    }
  };

  return (
    <div className="min-h-screen bg-background p-4 md:p-8 relative">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <h1>Device Connection Center</h1>
        <p className="text-muted-foreground">
          Connect to a device to enable the microphone
        </p>
        
        {/* Status Display */}
        {user && (
          <div className="mt-4 p-4 bg-card border rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Status:</span>
              <span className={`text-sm ${isRecording ? 'text-destructive' : isProcessing ? 'text-yellow-600' : 'text-muted-foreground'}`}>
                {isRecording ? '🎤 Recording...' : isProcessing ? '🔄 Processing...' : '⏸️ Ready'}
              </span>
            </div>
            {lastResponse && (
              <div className="mt-2 p-2 bg-muted rounded text-sm">
                <strong>Last Response:</strong> {lastResponse}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Device List */}
      <div className="max-w-xl mx-auto pb-32">
        {devices.map((device) => (
          <DeviceCard
            key={device.id}
            device={device}
            onToggle={toggleDevice}
          />
        ))}
      </div>

      {/* Center Round Button - Microphone */}
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-10">
        <button
          onClick={handleMicrophoneToggle}
          disabled={!hasConnectedDevice || isProcessing}
          className={`size-24 rounded-full shadow-2xl transition-all duration-300 flex items-center justify-center ${
            hasConnectedDevice && !isProcessing
              ? isRecording
                ? "bg-destructive text-destructive-foreground hover:scale-110 cursor-pointer hover:shadow-[0_0_40px_rgba(212,24,61,0.4)] active:scale-95"
                : "bg-primary text-primary-foreground hover:scale-110 cursor-pointer hover:shadow-[0_0_40px_rgba(3,2,19,0.3)] active:scale-95"
              : "bg-muted text-muted-foreground cursor-not-allowed opacity-50"
          }`}
        >
          {isProcessing ? (
            <div className="size-12 animate-spin rounded-full border-4 border-muted border-t-foreground"></div>
          ) : isRecording ? (
            <Mic className="size-12 animate-pulse" />
          ) : (
            <MicOff className="size-12" />
          )}
        </button>
        {hasConnectedDevice && (
          <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 whitespace-nowrap text-center">
            <p className="text-muted-foreground">
              {isProcessing ? "Processing audio..." : isRecording ? "Recording - Tap to stop" : "Tap to start recording"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}