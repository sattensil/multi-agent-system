import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# First try to load from the project root directory
env_path = Path(__file__).parents[2] / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"Loaded environment variables from {env_path}")
else:
    # Try to load from the current directory
    load_dotenv()
    print("Loaded environment variables from current directory")

# Check if OPENAI_API_KEY is set
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY environment variable is not set!")
    print("Please set it in your .env file or as an environment variable.")
    sys.exit(1)

# Check for News API key
news_api_key = os.getenv("NEWS_API_KEY")
if not news_api_key:
    print("\nNo News API key found. This is needed for reliable news sources.")
    print("You can get a free API key at https://newsapi.org/register")
    news_api_key = input("Enter your News API key (or press Enter to use fallback method): ").strip()
    
    if news_api_key:
        # Save the API key to .env file
        if env_path.exists():
            with open(env_path, "a") as f:
                f.write(f"\nNEWS_API_KEY={news_api_key}")
            print("News API key saved to .env file")
            # Reload environment variables
            load_dotenv(dotenv_path=env_path, override=True)

from .manager import LinkedInPostManager


async def main() -> None:
    """Main entry point for the LinkedIn post generation system."""
    print("\n=== LinkedIn Post Generator ===\n")
    
    # Get user preferences
    username = input("Enter your name or username for file naming (or press Enter for default): ")
    
    # Ask if user wants to search for news or input topics manually
    content_source = input("Do you want to: (1) Search for news articles, or (2) Input article URLs manually? (1/2, default: 1): ") or "1"
    
    if content_source == "1":
        # Search for news articles
        topics = input("Enter technology topics to search for (comma-separated, or press Enter for default): ")
        # Set default values if not provided
        topics = [t.strip() for t in topics.split(',')] if topics else ["AI", "machine learning", "software development", "data science", "tech innovation"]
        manual_articles = None
    else:
        # Input article URLs manually
        print("\nEnter article details manually (leave blank and press Enter when done):")
        manual_articles = []
        article_count = 1
        
        while True:
            print(f"\nArticle #{article_count}:")
            title = input("  Title: ")
            if not title:  # Exit if title is empty
                break
                
            url = input("  URL: ")
            source = input("  Source (e.g., TechCrunch, Wired): ")
            topic = input("  Main topic (this will be used for naming the post file): ")
            
            manual_articles.append({
                "title": title,
                "url": url,
                "source": source,
                "topic": topic,
                "date": "",  # Could add date input if needed
                "summary": ""  # Could add summary input if needed
            })
            
            article_count += 1
        
        # If no articles were entered, default to news search
        if not manual_articles:
            print("No articles entered. Defaulting to news search.")
            topics = ["AI", "machine learning", "software development", "data science", "tech innovation"]
            manual_articles = None
        else:
            # Set topics to empty list since we're using manual articles
            topics = []
    
    tone = input("Enter desired tone for posts (e.g., professional, conversational, technical) or press Enter for default: ")
    include_hashtags = input("Include hashtags? (y/n, default: y): ").lower() != 'n'
    
    # Function to select a persona
    def select_persona(prompt_text, default_persona=None):
        print(f"\n{prompt_text}")
        personas_dir = Path(__file__).parent / "personas"
        example_dir = personas_dir / "examples"
        
        # List available personas
        available_personas = []
        if personas_dir.exists():
            persona_files = list(personas_dir.glob("*.txt"))
            for i, file in enumerate(persona_files, 1):
                persona_name = file.stem.replace("_", " ").title()
                available_personas.append((persona_name, str(file)))
                print(f"{i}. {persona_name}")
        
        # If no custom personas found, check examples
        if not available_personas and example_dir.exists():
            example_files = list(example_dir.glob("*.txt"))
            for i, file in enumerate(example_files, 1):
                persona_name = file.stem.replace("_", " ").title()
                available_personas.append((persona_name, str(file)))
                print(f"{i}. {persona_name} (Example)")
        
        if available_personas:
            print(f"{len(available_personas) + 1}. Enter custom persona")
            print(f"{len(available_personas) + 2}. Create and save new persona")
            print(f"{len(available_personas) + 3}. Use default persona")
            
            persona_choice = input("\nSelect a persona option (number): ")
            
            if persona_choice.isdigit():
                choice_num = int(persona_choice)
                if 1 <= choice_num <= len(available_personas):
                    # Load persona from file
                    persona_file = available_personas[choice_num - 1][1]
                    with open(persona_file, "r") as f:
                        selected_persona = f.read().strip()
                    print(f"Loaded persona: {available_personas[choice_num - 1][0]}")
                    return selected_persona, available_personas[choice_num - 1][0]
                elif choice_num == len(available_personas) + 1:
                    # Enter custom persona for this session only
                    custom_persona = input("Enter your custom persona (for this session only): ")
                    return custom_persona, "Custom Persona"
                elif choice_num == len(available_personas) + 2:
                    # Create and save new persona
                    new_persona_name = input("Enter a name for your new persona (e.g., 'tech_expert'): ")
                    new_persona_name = new_persona_name.strip().lower().replace(" ", "_")
                    new_persona_content = input("Enter the persona description: ")
                    
                    # Ensure personas directory exists
                    personas_dir.mkdir(exist_ok=True)
                    
                    # Save the new persona
                    new_persona_path = personas_dir / f"{new_persona_name}.txt"
                    with open(new_persona_path, "w") as f:
                        f.write(new_persona_content)
                    
                    print(f"Saved new persona: {new_persona_name}")
                    return new_persona_content, new_persona_name.replace("_", " ").title()
                else:
                    # Use default
                    if default_persona:
                        return default_persona, "Default Persona"
                    return "", "Default Persona"
            else:
                # Invalid choice, use default
                if default_persona:
                    return default_persona, "Default Persona"
                return "", "Default Persona"
        else:
            # No personas available, use default or ask for custom
            if default_persona:
                return default_persona, "Default Persona"
            custom_persona = input("No personas found. Enter a custom persona: ")
            return custom_persona, "Custom Persona"
    
    # Get author's LinkedIn persona
    linkedin_persona, author_persona_name = select_persona("Select Author's LinkedIn Persona:")
    
    # Get target audience persona
    target_audience_persona, audience_persona_name = select_persona("Select Target Audience Persona:")
    
    # Get number of posts to generate
    num_posts_input = input("How many posts would you like to generate? (default: 5): ")
    num_posts = int(num_posts_input) if num_posts_input.isdigit() else 5
    
    # Get scheduling preference
    print("\nScheduling options:")
    print("1. Manual (copy/paste to LinkedIn)")
    print("2. Hootsuite (requires API key)")
    print("3. Later/Latermedia (requires API key)")
    print("4. LinkedIn Direct (requires API key)")
    scheduler_choice = input("Select scheduling option (1-4, default: 1): ") or "1"
    
    # Set default values if not provided
    username = username if username else "user"
    tone = tone if tone else "professional and insightful"
    
    # Note: topics is now handled in the content source selection section
    
    # Default personas if none selected
    personas_dir = Path(__file__).parent / "personas"
    example_dir = personas_dir / "examples"
    
    if not linkedin_persona:
        default_persona_file = example_dir / "tech_leader.txt"
        if default_persona_file.exists():
            with open(default_persona_file, "r") as f:
                linkedin_persona = f.read().strip()
                author_persona_name = "Tech Leader"
        else:
            linkedin_persona = "Technology thought leader focused on innovation and practical applications"
            author_persona_name = "Tech Leader"
    
    if not target_audience_persona:
        default_audience_file = example_dir / "data_scientist.txt"
        if default_audience_file.exists():
            with open(default_audience_file, "r") as f:
                target_audience_persona = f.read().strip()
                audience_persona_name = "Data Scientist"
        else:
            target_audience_persona = "Data scientist who translates complex analytics into practical business insights"
            audience_persona_name = "Data Scientist"
    
    # Map scheduler choice to scheduler name
    scheduler_map = {
        "1": "manual",
        "2": "hootsuite",
        "3": "later",
        "4": "linkedin"
    }
    scheduler = scheduler_map.get(scheduler_choice, "manual")
    
    # Additional preferences
    user_preferences = {
        "username": username,
        "topics": topics if content_source == "1" else [],  # Only include topics if using news search
        "tone": tone,
        "include_hashtags": include_hashtags,
        "scheduler": scheduler,
        "linkedin_persona": linkedin_persona,
        "num_posts": num_posts,
        "length": "2-3 paragraphs",
        "key_messages": [
            "Technology should solve real-world problems",
            "Innovation requires both creativity and discipline",
            "Continuous learning is essential in tech"
        ],
        "posting_frequency": "weekdays_only",
        "posting_time": "9:00 AM",
        "timezone": "America/Los_Angeles"
    }
    
    # Add manual articles if provided
    if content_source == "2" and manual_articles:
        user_preferences["manual_articles"] = manual_articles
    
    # Run the LinkedIn post generation workflow
    mgr = LinkedInPostManager()
    posts = await mgr.run(user_preferences)
    
    # Display the results
    print("\n=== Generated LinkedIn Posts ===\n")
    for i, post in enumerate(posts, 1):
        print(f"Post #{i} - Based on: {post['article']['title']}")
        print(f"Scheduled for: {post['scheduling']['scheduled_time']}")
        print("\n--- Content ---\n")
        print(post['content'])
        print("\n" + "-" * 50 + "\n")
    
    # Provide instructions for scheduling based on the selected option
    scheduler_name = scheduler.capitalize()
    print(f"\n=== Next Steps: {scheduler_name} Scheduling ===\n")
    
    if scheduler == "manual":
        print("To manually schedule these posts to LinkedIn:")
        print("1. Copy each post content")
        print("2. Paste it into LinkedIn's post creation interface")
        print("3. Schedule it for the recommended date and time")
        print("\nTip: You can use LinkedIn's built-in scheduling feature or any other social media tool")
    
    elif scheduler == "hootsuite":
        print("To use Hootsuite for scheduling:")
        print("1. Sign up for a Hootsuite account at https://hootsuite.com if you don't have one")
        print("2. Connect your LinkedIn profile to Hootsuite")
        print("3. Get an API key from Hootsuite's developer portal")
        print("4. Add your Hootsuite API key to your .env file as HOOTSUITE_ACCESS_TOKEN")
        print("\nNote: You'll need a Hootsuite paid plan to access their API")
    
    elif scheduler == "later":
        print("To use Later for scheduling:")
        print("1. Sign up for a Later account at https://later.com if you don't have one")
        print("2. Connect your LinkedIn profile to Later")
        print("3. Get an API key from Later's developer portal")
        print("4. Add your Later API key to your .env file as LATER_API_KEY")
    
    elif scheduler == "linkedin":
        print("To use LinkedIn's direct API for posting:")
        print("1. Create a LinkedIn Developer application at https://www.linkedin.com/developers/")
        print("2. Request the necessary permissions for posting content")
        print("3. Generate an access token with the required scopes")
        print("4. Add your LinkedIn access token to your .env file as LINKEDIN_ACCESS_TOKEN")
        print("\nNote: LinkedIn's API doesn't support scheduling, so posts will be published immediately")


if __name__ == "__main__":
    asyncio.run(main())
