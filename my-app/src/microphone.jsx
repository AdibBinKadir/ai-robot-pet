import { useState } from "react";
import { DeviceCard } from "./components/DeviceCard.jsx";
import { Mic, MicOff } from "lucide-react";
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

  const hasConnectedDevice = devices.some(
    (device) => device.status === "connected"
  );

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

  const handleMicrophoneToggle = () => {
    if (hasConnectedDevice) {
      setIsMicOn((prev) => !prev);
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
          disabled={!hasConnectedDevice}
          className={`size-24 rounded-full shadow-2xl transition-all duration-300 flex items-center justify-center ${
            hasConnectedDevice
              ? isMicOn
                ? "bg-destructive text-destructive-foreground hover:scale-110 cursor-pointer hover:shadow-[0_0_40px_rgba(212,24,61,0.4)] active:scale-95"
                : "bg-primary text-primary-foreground hover:scale-110 cursor-pointer hover:shadow-[0_0_40px_rgba(3,2,19,0.3)] active:scale-95"
              : "bg-muted text-muted-foreground cursor-not-allowed opacity-50"
          }`}
        >
          {isMicOn ? (
            <Mic className="size-12 animate-pulse" />
          ) : (
            <MicOff className="size-12" />
          )}
        </button>
        {hasConnectedDevice && (
          <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 whitespace-nowrap text-center">
            <p className="text-muted-foreground">
              {isMicOn ? "Microphone Active" : "Tap to activate mic"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}