import os
import json
import google.generativeai as genai

class RobotCommandProcessor:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Robot action mappings (easily expandable)
        self.actions = {
            0: "do nothing",
            1: "go forward", 
            2: "go backward",
            3: "turn left",
            4: "turn right"
        }
        
        # Voice responses for each action
        self.voice_responses = {
            0: "I understand.",
            1: "Moving forward now.",
            2: "Going backward.",
            3: "Turning left.",
            4: "Turning right."
        }
    
    def create_command_detection_prompt(self, user_input):
        """Create a prompt to detect if input is a robot command or conversation."""
        return f"""
You are a friendly robot assistant that can both have conversations and perform movement actions.

Analyze the user's input and determine if they want:
1. A robot movement action (forward, backward, left, right, stop)
2. Just a normal conversation

Available robot actions:
- Action 1: Go forward / Move forward / Move ahead / Advance / Go straight
- Action 2: Go backward / Move backward / Move back / Reverse / Back up
- Action 3: Turn left / Rotate left / Left turn / Go left  
- Action 4: Turn right / Rotate right / Right turn / Go right

User input: "{user_input}"

If this is a MOVEMENT COMMAND, respond with JSON:
{{"action": <number>, "response": "Moving forward now.", "is_command": true}}

If this is just CONVERSATION, respond with JSON:
{{"action": 0, "response": "<your conversational response>", "is_command": false}}

Examples:
- "go forward" -> {{"action": 1, "response": "Moving forward now.", "is_command": true}}
- "hello how are you?" -> {{"action": 0, "response": "Hello! I'm doing great, thank you for asking. How can I help you today?", "is_command": false}}
- "turn left please" -> {{"action": 3, "response": "Turning left.", "is_command": true}}
- "what's your name?" -> {{"action": 0, "response": "I'm your friendly robot assistant! You can give me movement commands or just chat with me.", "is_command": false}}

Be conversational and friendly for non-movement inputs. Only use actions 0-4 for actual movement commands.
"""
    
    def process_input(self, user_input):
        """Process user input - either conversation or robot command."""
        try:
            prompt = self.create_command_detection_prompt(user_input)
            response = self.model.generate_content(prompt)
            
            # Clean the response text and extract JSON
            response_text = response.text.strip()
            print(f"Raw AI Response: {response_text}")  # Debug output
            
            # Try to extract JSON from the response
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_text = response_text[start:end]
                result = json.loads(json_text)
            else:
                # Fallback: try to parse the entire response
                result = json.loads(response_text)
            
            action_number = result.get('action', 0)
            ai_response = result.get('response', 'I understand.')
            is_command = result.get('is_command', False)
            
            if is_command and action_number in self.actions:
                # This is a robot command
                return {
                    'type': 'command',
                    'action_number': action_number,
                    'action_name': self.actions[action_number],
                    'voice_output': ai_response,
                    'user_input': user_input
                }
            else:
                # This is conversation - action 0 (do nothing)
                return {
                    'type': 'conversation',
                    'action_number': 0,
                    'action_name': 'conversation',
                    'voice_output': ai_response,
                    'user_input': user_input
                }
            
        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"Error processing input: {e}")  # Debug output
            print(f"Raw response was: {response.text if 'response' in locals() else 'No response'}")
            
            # Try simple keyword matching as fallback for commands
            fallback_action = self._fallback_command_matching(user_input)
            
            if fallback_action > 0:  # It's likely a command
                return {
                    'type': 'command',
                    'action_number': fallback_action,
                    'action_name': self.actions[fallback_action],
                    'voice_output': self.voice_responses[fallback_action],
                    'user_input': user_input,
                    'error': f"Used fallback matching due to: {str(e)}"
                }
            else:
                # Treat as conversation - action 0 (do nothing)
                return {
                    'type': 'conversation',
                    'action_number': 0,
                    'action_name': 'conversation',
                    'voice_output': "I'm not sure I understood that, but I'm here to chat or help you move around!",
                    'user_input': user_input,
                    'error': f"Fallback conversation due to: {str(e)}"
                }
    
    def _fallback_command_matching(self, user_input):
        """Simple keyword-based fallback for command matching."""
        user_input_lower = user_input.lower()
        
        # Check for forward commands
        if any(word in user_input_lower for word in ['forward', 'ahead', 'straight', 'front']):
            return 1
        
        # Check for backward commands
        if any(word in user_input_lower for word in ['backward', 'back', 'reverse']):
            return 2
            
        # Check for left commands
        if any(word in user_input_lower for word in ['left']):
            return 3
            
        # Check for right commands
        if any(word in user_input_lower for word in ['right']):
            return 4
        
        # Default to do nothing (conversation)
        return 0
    
    def add_action(self, action_number, action_name, voice_response):
        """Add new actions for scalability."""
        self.actions[action_number] = action_name
        self.voice_responses[action_number] = voice_response

def read_api_key(env_file='keys.env', key_name='GEMINI_API_KEY'):
    with open(env_file, 'r') as f:
        for line in f:
            if line.startswith(key_name + '='):
                return line.strip().split('=', 1)[1]
    raise ValueError(f"{key_name} not found in {env_file}")

def main():
    """Main function to run the robot assistant."""
    try:
        api_key = read_api_key()
        robot = RobotCommandProcessor(api_key)
        
        print("🤖 Friendly Robot Assistant Started!")
        print("I can chat with you OR perform these actions: forward, backward, left, right")
        print("Type 'quit' to exit\n")
        
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Robot: Goodbye! It was nice talking with you. 👋")
                break
            
            if not user_input:
                continue
                
            # Process the input (conversation or command)
            result = robot.process_input(user_input)
            
            # Output based on type
            if result['type'] == 'command':
                print(f"Robot: {result['voice_output']}")
                print(f"🎯 Action Number: {result['action_number']} ({result['action_name']})")
            else:
                print(f"Robot: {result['voice_output']}")
            
            if 'error' in result:
                print(f"⚠️  Debug: {result['error']}")
            
            print("-" * 60)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()