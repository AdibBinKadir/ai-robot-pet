import { Wifi, Smartphone, Laptop, Watch, Speaker } from "lucide-react";
import { Card } from "./ui/card.tsx";

const iconMap = {
  phone: Smartphone,
  laptop: Laptop,
  watch: Watch,
  speaker: Speaker,
};

export function DeviceCard({ device, onToggle }) {
  const Icon = iconMap[device.type];
  const isConnected = device.status === "connected";

  return (
    <Card
      onClick={() => onToggle(device.id)}
      className={`p-10 md:p-12 cursor-pointer transition-all duration-300 hover:shadow-xl ${
        isConnected
          ? "bg-primary text-primary-foreground border-primary"
          : "bg-card hover:bg-accent"
      }`}
    >
      <div className="flex items-center gap-8">
        <div
          className={`p-6 md:p-8 rounded-2xl ${
            isConnected ? "bg-primary-foreground/10" : "bg-muted"
          }`}
        >
          <Icon className="size-12 md:size-16" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className={isConnected ? "text-primary-foreground" : ""}>
            {device.name}
          </h3>
          <p
            className={
              isConnected ? "text-primary-foreground/70" : "text-muted-foreground"
            }
          >
            {isConnected ? "Connected" : "Available"}
          </p>
        </div>
        {isConnected && (
          <div className="flex-shrink-0">
            <Wifi className="size-8 md:size-10 animate-pulse" />
          </div>
        )}
      </div>
    </Card>
  );
}