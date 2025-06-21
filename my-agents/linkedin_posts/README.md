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

## Scheduling Options

This system supports multiple ways to schedule your LinkedIn posts:

### 1. Manual Scheduling

The default option that requires no API keys:
- Copy the generated posts and paste them into LinkedIn's post creation interface
- Use LinkedIn's built-in scheduling feature to set the posting time

### 2. Hootsuite Integration

For automated scheduling via [Hootsuite](https://hootsuite.com):
1. Sign up for Hootsuite and connect your LinkedIn profile
2. Get a Hootsuite API key from their developer portal (requires paid plan)
3. Add the token to your `.env` file as `HOOTSUITE_ACCESS_TOKEN`

### 3. Later/Latermedia Integration

For automated scheduling via [Later](https://later.com):
1. Sign up for Later and connect your LinkedIn profile
2. Get a Later API key from their developer portal
3. Add the key to your `.env` file as `LATER_API_KEY`

### 4. LinkedIn Direct Integration

For posting directly to LinkedIn (no scheduling):
1. Create a LinkedIn Developer application
2. Request the necessary permissions for posting content
3. Generate an access token with the required scopes
4. Add the token to your `.env` file as `LINKEDIN_ACCESS_TOKEN`

Note: LinkedIn's API doesn't support scheduling, so posts will be published immediately

## Structure

- `main.py`: Entry point and user interface
- `manager.py`: Orchestrates the multi-agent workflow
- `buffer_integration.py`: Handles integrations with social media platforms (despite the filename, now supports multiple platforms)

## Extending

You can extend this system by:
- Adding support for other social media platforms
- Implementing custom news sources
- Creating specialized agents for different content types
- Enhancing the scheduling logic

## GitHub Integration

This project includes a `.gitignore` file that excludes:

- Environment variables (`.env` file with API keys)
- Generated posts directory
- Custom persona files (except examples)

This ensures that sensitive information and personal content aren't accidentally pushed to public repositories.

## License

This project is part of the multi-agent-system framework.
