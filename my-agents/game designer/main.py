import asyncio
import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

# Add the main project directory to the Python path
main_dir = Path(__file__).parents[2]  # Go up to the main project directory
sys.path.insert(0, str(main_dir))

# Add the openai-agents-python/src directory to the Python path
agents_dir = main_dir / 'openai-agents-python' / 'src'
sys.path.insert(0, str(agents_dir))

# Load environment variables from .env file in the main directory
env_path = main_dir / '.env'

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"Loaded environment variables from {env_path}")
else:
    # Fallback to looking in other common locations
    alt_env_path = Path(__file__).parent.parent.parent / '.env'  # Alternative path
    if alt_env_path.exists():
        load_dotenv(dotenv_path=alt_env_path)
        print(f"Loaded environment variables from {alt_env_path}")
    else:
        # Last resort - try current directory
        load_dotenv()
        print("Loaded environment variables from current directory")

# Check if OPENAI_API_KEY is set
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY environment variable is not set!")
    print("Please set it in your .env file or as an environment variable.")
    sys.exit(1)

# Change relative import to absolute import
from manager import BoardGameDesignManager


def parse_game_concept(concept_text):
    """Parse the user's free-form game concept text to extract key parameters using OpenAI function calling."""
    import json
    from openai import OpenAI
    
    print("\n[STATUS] Initializing OpenAI client for game concept parsing...")
    # Initialize OpenAI client with API key from environment
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Define the function schema for OpenAI function calling
    game_schema = {
        "name": "extract_game_parameters",
        "description": "Extract structured board game design parameters from freeform text",
        "parameters": {
            "type": "object",
            "properties": {
                "game_name": {
                    "type": "string",
                    "description": "The title or name of the board game"
                },
                "theme": {
                    "type": "string",
                    "description": "The theme of the game (e.g., fantasy, sci-fi, historical, modern, abstract, educational, mystery, horror, adventure)"
                },
                "player_count": {
                    "type": "string",
                    "description": "The number of players the game supports (e.g., '2-4', '1-6', '3')"
                },
                "complexity": {
                    "type": "string",
                    "description": "The complexity level of the game (light, medium, heavy)"
                },
                "duration": {
                    "type": "string",
                    "description": "Estimated playtime in minutes (e.g., '30', '60-90')"
                },
                "design_focus": {
                    "type": "string",
                    "description": "The primary gameplay focus (e.g., strategy, luck, social, creativity, knowledge, dexterity, resource management, exploration, combat)"
                },
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of specific constraints or requirements (e.g., family friendly, educational, portable, historical accuracy)"
                }
            },
            "required": ["theme"]
        }
    }
    
    # Call the OpenAI API with function calling
    try:
        print("\n[STATUS] Sending game description to OpenAI for parsing...")
        print("This may take a few moments. Please wait...")
        response = client.chat.completions.create(
            model="gpt-4",  # Using a model that supports function calling
            messages=[
                {"role": "system", "content": "You are a board game design expert who extracts structured information from game concept descriptions."},
                {"role": "user", "content": concept_text}
            ],
            functions=[game_schema],
            function_call={"name": "extract_game_parameters"}
        )
        
        print("\n[STATUS] OpenAI response received. Extracting structured data...")
        
        # Extract the structured data from the response
        function_call = response.choices[0].message.function_call
        if function_call and function_call.name == "extract_game_parameters":
            parsed_data = json.loads(function_call.arguments)
            
            print("\n[STATUS] Successfully parsed game concept into structured data!")
            print(f"[STATUS] Extracted game name: {parsed_data.get('game_name', 'Not specified')}")
            print(f"[STATUS] Extracted theme: {parsed_data.get('theme', 'Not specified')}")
            
            # Apply defaults for missing values
            if not parsed_data.get("player_count"):
                parsed_data["player_count"] = "2-4"
                print(f"[STATUS] Using default player count: {parsed_data['player_count']}")
            if not parsed_data.get("complexity"):
                parsed_data["complexity"] = "medium"
                print(f"[STATUS] Using default complexity: {parsed_data['complexity']}")
            if not parsed_data.get("duration"):
                parsed_data["duration"] = "30"
                print(f"[STATUS] Using default duration: {parsed_data['duration']} minutes")
            if not parsed_data.get("constraints"):
                parsed_data["constraints"] = []
            
            # Store the entire concept as custom_restrictions to preserve all details
            parsed_data["custom_restrictions"] = concept_text
            
            print("\n[STATUS] Game concept parsing complete!")
            return parsed_data
        else:
            error_message = "ERROR: OpenAI function calling failed to extract game parameters."
            print(error_message)
            sys.exit(1)
    except Exception as e:
        error_message = f"ERROR: OpenAI service failed to parse the game concept: {e}"
        print(error_message)
        print("Please check your internet connection and API key, then try again.")
        sys.exit(1)
    


def get_multiline_input(prompt):
    """Get multi-line input from the user until they enter an empty line."""
    print(prompt)
    print("(Type your complete description below. When finished, press Enter on an empty line)")
    print("-------- Start typing your game concept below this line --------")
    
    lines = []
    line_count = 0
    while True:
        try:
            line = input()
            if not line.strip():  # Empty line
                if lines:  # Only break if we have at least one line of content
                    print("\n[STATUS] Input complete. Processing your game concept...")
                    break
                else:
                    print("[STATUS] No input detected. Please describe your game concept:")
                    continue
            
            lines.append(line)
            line_count += 1
            if line_count % 5 == 0:  # Give feedback every 5 lines
                print(f"[STATUS] Received {line_count} lines so far. Continue typing or press Enter on an empty line when done.")
        except KeyboardInterrupt:
            print("\n[STATUS] Input interrupted. Processing what you've entered so far...")
            break
        except EOFError:
            print("\n[STATUS] Input ended. Processing your game concept...")
            break
    
    return "\n".join(lines)


def verify_parameter(param_name, current_value, description):
    """Verify a game parameter with the user and allow them to modify it."""
    while True:
        print(f"\n{description}: {current_value}")
        response = input(f"Is this {param_name} correct? (y/n): ").strip().lower()
        
        if response == 'y' or response == 'yes':
            return current_value
        elif response == 'n' or response == 'no':
            new_value = input(f"Please enter the correct {param_name}: ").strip()
            if new_value:  # Make sure we don't accept empty values
                return new_value
            print("Value cannot be empty. Using the original value.")
            return current_value
        else:
            print("Please enter 'y' or 'n'.")

async def main() -> None:
    """Main entry point for the Board Game Designer system."""
    print("\n[STATUS] Multi-Agent Board Game Designer System Starting...")
    print("[STATUS] All status updates about API calls and processing will be shown throughout execution.")
    print("\n====================================================")
    print("         MULTI-AGENT BOARD GAME DESIGNER        ")
    print("====================================================")
    
    print("\nDescribe your board game concept in as much detail as you like.")
    print("You can include theme, player count, complexity, game duration, and any special requirements.")
    print("Feel free to write as much as you want - the more details you provide, the better!")
    print("\nFor example, you could describe:")
    print("- The theme and setting")
    print("- Number of players and target audience")
    print("- Game complexity and duration")
    print("- Mechanics and gameplay elements you'd like to see")
    print("- Any specific constraints or historical accuracy requirements")
    print("- Unique features or inspirations from other games")
    print("\n[STATUS] Waiting for your game concept description...\n")
    
    # Get the initial game concept with multi-line support
    concept_text = get_multiline_input("Enter your game concept:")
    
    # Parse the game concept to extract structured parameters
    parsed_data = parse_game_concept(concept_text)
    
    # Store the original description for the project manager
    original_description = concept_text
    
    # Parameter verification step
    print("\n[STATUS] Please verify the extracted game parameters:\n")
    print("======================================================")
    
    # Verify each parameter with the user
    game_name = verify_parameter(
        "game name", 
        parsed_data.get("game_name", "Unnamed Game"), 
        "Game Name")
        
    theme = verify_parameter(
        "theme", 
        parsed_data.get("theme", "Not specified"), 
        "Theme")
        
    player_count = verify_parameter(
        "player count", 
        parsed_data.get("player_count", "2-4"), 
        "Player Count (e.g., '2-4', '1-6')")
        
    complexity = verify_parameter(
        "complexity", 
        parsed_data.get("complexity", "medium"), 
        "Complexity (light, medium, heavy)")
        
    duration = verify_parameter(
        "duration", 
        parsed_data.get("duration", "30"), 
        "Duration in minutes (e.g., '30', '60-90')")
        
    design_focus = verify_parameter(
        "design focus", 
        parsed_data.get("design_focus", "strategy"), 
        "Primary Gameplay Focus (e.g., strategy, luck, social)")
    
    # Verify constraints if they exist
    constraints = parsed_data.get("constraints", [])
    if constraints:
        print("\nCurrent Constraints:")
        for i, constraint in enumerate(constraints):
            print(f"{i+1}. {constraint}")
        
        response = input("\nWould you like to modify these constraints? (y/n): ").strip().lower()
        if response == 'y' or response == 'yes':
            new_constraints = []
            while True:
                constraint = input("Enter a constraint (or leave empty to finish): ").strip()
                if not constraint:
                    break
                new_constraints.append(constraint)
            
            if new_constraints:
                constraints = new_constraints
            else:
                print("No new constraints provided. Keeping the original constraints.")
    else:
        print("\nNo constraints specified.")
        response = input("Would you like to add constraints? (y/n): ").strip().lower()
        if response == 'y' or response == 'yes':
            constraints = []
            while True:
                constraint = input("Enter a constraint (or leave empty to finish): ").strip()
                if not constraint:
                    break
                constraints.append(constraint)
    
    # Create the final user preferences dictionary with verified parameters
    user_preferences = {
        "game_name": game_name,
        "theme": theme,
        "player_count": player_count,
        "complexity": complexity,
        "duration": duration,
        "design_focus": design_focus,
        "constraints": constraints,
        "custom_restrictions": original_description,  # Preserve original description
        "original_description": original_description  # Extra field to make sure it's accessible
    }
    
    print("\n[STATUS] Parameter verification complete!")
    print("======================================================")
    print("\n[STATUS] Starting game design process with verified parameters...")
    
    # Initialize the game design manager
    board_game_manager = BoardGameDesignManager()
    print(f"Designing a {user_preferences['theme']} game with the following details:")
    print(f"- Player Count: {user_preferences['player_count']}")
    print(f"- Complexity: {user_preferences['complexity']}")
    print(f"- Estimated Duration: {user_preferences['duration']} minutes")
    
    if user_preferences["design_focus"]:
        print(f"- Focus: {user_preferences['design_focus']}")
        
    print("\nThis process may take several minutes as our agents collaborate on your game design.")
    print("The system will generate comprehensive documentation in the 'generated_games' directory.")
    print("\nWorking on your game design...\n")
    
    manager = BoardGameDesignManager()
    game_design = await manager.run(user_preferences)
    
    # Display results summary
    print("\n=== Game Design Complete ===\n")
    print(f"Game: {game_design['game_name']}")
    print(f"Theme: {game_design['theme']}")
    print(f"Players: {game_design['player_count']}")
    print(f"Playtime: {game_design['duration']} minutes")
    print(f"Complexity: {game_design['complexity']}")
    
    # Indicate where the full design document can be found
    output_dir = Path(__file__).parent / "generated_games" / game_design['game_name'].replace(" ", "_")
    print(f"\nComplete game design documents can be found in: {output_dir}")
    print("\nThank you for using the Multi-Agent Board Game Designer!")


if __name__ == "__main__":
    asyncio.run(main())
