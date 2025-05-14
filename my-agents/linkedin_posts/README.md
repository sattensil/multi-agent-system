# LinkedIn Post Generator

A multi-agent system for automatically generating, editing, and scheduling LinkedIn posts based on recent technology news and trending topics.

## Overview

This system uses a workflow of specialized AI agents to:

1. **Search for News**: Finds relevant tech news articles and trending topics from reliable sources using News API
2. **Write LinkedIn Posts**: Drafts authentic, story-driven posts that avoid marketing language
3. **Edit and Refine**: Adjusts content to maintain conversational tone and address "why should I care" questions
4. **Revise Based on Feedback**: Creates polished final versions that sound like real conversations
5. **Prepare for Scheduling**: Formats posts for scheduling via various methods
6. **Save as Files**: Stores generated posts as markdown files with user, date, and topic in the filename

## Prerequisites

- Python 3.9+
- OpenAI API key (set in your `.env` file)
- News API key (recommended for reliable news sources, get one at https://newsapi.org/register)
- For automated scheduling (optional):
  - Hootsuite account and API key, OR
  - Later/Latermedia account and API key, OR
  - LinkedIn Developer account with API access

## Installation

1. Ensure you have the required dependencies:
   ```
   pip install openai python-dotenv requests
   ```

2. Set up your environment variables in a `.env` file:
   ```
   OPENAI_API_KEY=your_openai_api_key
   NEWS_API_KEY=your_news_api_key
   # Optional, for automated scheduling (choose one based on your preferred platform):
   HOOTSUITE_ACCESS_TOKEN=your_hootsuite_token
   LATER_API_KEY=your_later_api_key
   LINKEDIN_ACCESS_TOKEN=your_linkedin_token
   ```

## Usage

Run the LinkedIn post generator:

```bash
cd /Users/scarlettattensil/Documents/github/multi-agent-system
python -m my-agents.linkedin_posts.main
```

The script will:
1. Prompt you for your name/username (for file naming)
2. Ask for topics to search for
3. Request your preferred tone
4. Show available LinkedIn personas and let you:
   - Select an existing persona from file
   - Enter a custom persona for the current session
   - Create and save a new persona for future use
   - Use the default persona
5. Determine how many posts to generate (up to 20)
6. Select scheduling preferences
7. Confirm if you want to include hashtags
8. Generate LinkedIn posts based on recent news and trending topics
9. Display the posts and scheduling information
10. Save posts as markdown files in the `generated_posts` directory

## Customization

You can customize the following aspects:
- Topics of interest
- Post tone and style
- LinkedIn personas (saved as text files)
- Branding and key messages
- Posting frequency and schedule
- Hashtag preferences

Edit the `user_preferences` dictionary in `main.py` to set default values.

### Managing Personas

Personas are stored as text files in the `personas` directory. Each file contains a description of a LinkedIn persona that will be used to guide the tone and style of your posts.

#### Sample Personas

The system comes with example personas in the `personas/examples` directory:

- **Tech Leader**: Technology thought leader focused on innovation and practical applications
- **Data Scientist**: Data scientist who translates complex analytics into practical business insights
- **Startup Founder**: Startup founder sharing the unfiltered journey of building a company

#### Creating Your Own Personas

You can create your own personas in two ways:

1. **Through the CLI**: Select "Create and save new persona" when prompted
2. **Manually**: Create a text file in the `personas` directory with a descriptive name (e.g., `industry_expert.txt`) containing your persona description

