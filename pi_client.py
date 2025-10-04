#!/usr/bin/env python3
"""
PI CLIENT - Polls command server and executes robot actions
Runs on Raspberry Pi, connects to Flask server for commands
"""

import time
import json
import requests
from datetime import datetime

class PiRobotClient:
    """
    Client that runs on Raspberry Pi to execute robot commands.
    Polls the Flask server for new commands and executes them.
    """
    
    def __init__(self, server_url="http://localhost:5000"):
        """
        Initialize Pi client.
        
        Args:
            server_url (str): URL of the Flask command server
        """
        self.server_url = server_url.rstrip('/')
        self.poll_interval = 1.0  # seconds
        self.running = False
        
        print(f"🤖 Pi Robot Client initialized")
        print(f"🌐 Server: {self.server_url}")
    
    def execute_robot_action(self, action_number):
        """
        Execute robot action based on action number.
        
        Args:
            action_number (int): 0-4 robot action
            
        Returns:
            bool: True if successful
        """
        try:
            print(f"🎯 Executing action {action_number}")
            
            if action_number == 0:
                print("💬 Conversational response - no robot movement")
                return True
            elif action_number == 1:
                print("➡️  MOVE FORWARD")
                # TODO: Add actual robot movement code here
                # robot.move_forward()
                time.sleep(0.5)  # Simulate movement time
                return True
            elif action_number == 2:
                print("⬅️  TURN LEFT")
                # TODO: Add actual robot movement code here
                # robot.turn_left()
                time.sleep(0.5)
                return True
            elif action_number == 3:
                print("➡️  TURN RIGHT") 
                # TODO: Add actual robot movement code here
                # robot.turn_right()
                time.sleep(0.5)
                return True
            elif action_number == 4:
                print("⬇️  MOVE BACKWARD")
                # TODO: Add actual robot movement code here
                # robot.move_backward()
                time.sleep(0.5)
                return True
            else:
                print(f"❌ Unknown action number: {action_number}")
                return False
                
        except Exception as e:
            print(f"❌ Error executing action {action_number}: {e}")
            return False
    
    def poll_for_commands(self):
        """
        Poll server for new commands and execute them.
        """
        try:
            response = requests.get(f"{self.server_url}/api/get-commands", timeout=5)
            response.raise_for_status()
            
            data = response.json()
            commands = data.get('commands', [])
            
            for command in commands:
                try:
                    print(f"\n📨 New command: {command['id']}")
                    print(f"🎤 User said: '{command['transcription']}'")
                    print(f"💭 Response: '{command['voice_response']}'")
                    
                    # Execute the robot action
                    success = self.execute_robot_action(command['action_number'])
                    
                    if success:
                        # Mark command as processed
                        mark_response = requests.post(
                            f"{self.server_url}/api/mark-processed",
                            json={'command_id': command['id']},
                            timeout=5
                        )
                        mark_response.raise_for_status()
                        print(f"✅ Command {command['id']} completed")
                    else:
                        print(f"❌ Failed to execute command {command['id']}")
                        
                except Exception as e:
                    print(f"❌ Error processing command {command.get('id', 'unknown')}: {e}")
            
            return len(commands)
            
        except requests.exceptions.RequestException as e:
            print(f"🌐 Connection error: {e}")
            return 0
        except Exception as e:
            print(f"❌ Error polling for commands: {e}")
            return 0
    
    def check_server_status(self):
        """
        Check if server is reachable.
        
        Returns:
            bool: True if server is online
        """
        try:
            response = requests.get(f"{self.server_url}/api/status", timeout=5)
            response.raise_for_status()
            
            data = response.json()
            print(f"🟢 Server online - {data.get('pending_commands', 0)} pending commands")
            return True
            
        except Exception as e:
            print(f"🔴 Server unreachable: {e}")
            return False
    
    def run(self):
        """
        Main run loop - polls for commands continuously.
        """
        print(f"🚀 Starting Pi Robot Client...")
        
        # Check server connection
        if not self.check_server_status():
            print("❌ Cannot connect to server. Exiting.")
            return
        
        self.running = True
        print(f"🔄 Polling every {self.poll_interval} seconds...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                commands_processed = self.poll_for_commands()
                
                if commands_processed > 0:
                    print(f"📊 Processed {commands_processed} commands")
                
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping Pi Robot Client...")
            self.running = False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            self.running = False


def main():
    """
    Main function - create and run Pi client.
    """
    import sys
    
    # Get server URL from command line or use default
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    # Create and run client
    client = PiRobotClient(server_url)
    client.run()


if __name__ == "__main__":
    main()