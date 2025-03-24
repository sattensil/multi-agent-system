import asyncio
import os
import re
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dotenv import load_dotenv

from agents import Agent, Runner
from agents.result import RunResult
from .buffer_integration import SocialMediaScheduler, HootsuiteIntegration, LatermediaIntegration, LinkedInDirectIntegration

# Load environment variables
load_dotenv()

class LinkedInPostManager:
    """Manager for the LinkedIn post generation workflow."""

    def __init__(self, username: str = "user", topics: List[str] = None, tone: str = "professional", 
                 linkedin_persona: str = None, target_audience_persona: str = None,
                 author_persona_name: str = "Default", audience_persona_name: str = "Default",
                 include_hashtags: bool = True, scheduler: str = "manual"):
        """Initialize the LinkedIn post manager.
        
        Args:
            username: Username for file naming
            topics: List of topics to search for
            tone: Desired tone for the posts
            linkedin_persona: Author's LinkedIn persona description
            target_audience_persona: Target audience persona description
            author_persona_name: Name of the author persona
            audience_persona_name: Name of the audience persona
            include_hashtags: Whether to include hashtags in posts
            scheduler: Scheduling method to use
        """
        # Store user preferences
        self.user_preferences = {
            "username": username,
            "topics": topics or ["AI", "machine learning", "software development"],
            "tone": tone,
            "linkedin_persona": linkedin_persona or "Technology thought leader focused on innovation",
            "target_audience_persona": target_audience_persona or "Technology professional interested in practical insights",
            "author_persona_name": author_persona_name,
            "audience_persona_name": audience_persona_name,
            "include_hashtags": include_hashtags,
            "scheduler": scheduler
        }
        
        # Initialize agents
        self.news_searcher_agent = self._create_news_searcher_agent()
        self.post_writer_agent = self._create_post_writer_agent()
        self.editor_agent = self._create_editor_agent()
        self.reviser_agent = self._create_reviser_agent()

    async def run(self, user_preferences: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """
        Run the LinkedIn post generation workflow.
        
        Args:
            user_preferences: Optional dictionary of user preferences to override the defaults
            
        Returns:
            List of dictionaries containing the final LinkedIn posts with metadata
        """
        print("✅ Starting LinkedIn post generation...")
        
        # Update user preferences if provided
        if user_preferences:
            # Create a deep copy of the existing preferences
            updated_preferences = dict(self.user_preferences)
            # Update with the new preferences
            updated_preferences.update(user_preferences)
            # Set as the current preferences
            self.user_preferences = updated_preferences
        
        # Get the number of posts to generate (default to 5 if not specified)
        num_posts = self.user_preferences.get("num_posts", 5)
        
        # Step 1: Get articles (either from search or manual input)
        manual_articles = self.user_preferences.get("manual_articles")
        
        if manual_articles:
            print(f"⏳ Using {len(manual_articles)} manually entered articles...")
            news_articles = manual_articles
            # Debug: Print details of manual articles
            for i, article in enumerate(manual_articles):
                print(f"  - Manual article {i+1}: {article.get('title', 'Untitled')} (Topic: {article.get('topic', 'None')})")
        else:
            # Search for articles using the News API
            print(f"⏳ Searching for recent technology news to generate {num_posts} posts...")
            news_articles = await self._search_tech_news(self.user_preferences.get("topics", []), num_posts)
            
        print(f"✅ Found {len(news_articles)} relevant news articles")
        
        # Step 2: Generate post drafts
        print("⏳ Writing LinkedIn post drafts...")
        post_drafts = await self._write_post_drafts(news_articles)
        print(f"✅ Generated {len(post_drafts)} post drafts")
        print(f"  - Draft titles: {', '.join([draft['article'].get('title', 'Untitled')[:30] + '...' for draft in post_drafts])}")
        
        # Step 3: Edit and refine posts
        print("⏳ Editing and refining posts...")
        edited_posts = await self._edit_posts(post_drafts)
        print(f"✅ Edited {len(edited_posts)} posts")
        print(f"  - Edited titles: {', '.join([post['article'].get('title', 'Untitled')[:30] + '...' for post in edited_posts])}")
        
        # Step 4: Revise based on feedback
        print("⏳ Revising posts based on feedback...")
        final_posts = await self._revise_posts(edited_posts)
        print(f"✅ Finalized {len(final_posts)} LinkedIn posts")
        print(f"  - Final titles: {', '.join([post['article'].get('title', 'Untitled')[:30] + '...' for post in final_posts])}")
        
        # Step 5: Schedule posts
        print("⏳ Preparing posts for scheduling...")
        scheduled_posts = await self._prepare_for_scheduling(final_posts)
        print(f"✅ Prepared {len(scheduled_posts)} posts for scheduling")
        print(f"  - Scheduled titles: {', '.join([post['article'].get('title', 'Untitled')[:30] + '...' for post in scheduled_posts])}")
        
        # Step 6: Save posts as separate markdown files
        if scheduled_posts:
            self._save_posts_as_files(scheduled_posts, self.user_preferences)
        
        return scheduled_posts

    async def _search_tech_news(self, topics: List[str], num_posts: int = 5) -> List[Dict[str, str]]:
        """
        Search for recent technology news and trending topics using News API.
        
        Args:
            topics: List of technology topics to search for
            num_posts: Number of posts to generate (affects how many news articles to find)
            
        Returns:
            List of news article dictionaries with title, url, summary, etc.
        """
        # Get News API key from environment variables
        news_api_key = os.getenv("NEWS_API_KEY")
        if not news_api_key:
            print("⚠️ NEWS_API_KEY not found in environment variables. Using fallback search method.")
            return await self._fallback_search_tech_news(topics, num_posts)
        
        # Calculate articles per topic to fetch
        if len(topics) > 0:
            # Distribute the requested number of posts across topics
            articles_per_topic = max(1, num_posts // len(topics))
            # Ensure we don't exceed the total requested number of posts
            total_articles = articles_per_topic * len(topics)
            if total_articles > num_posts:
                # If we have too many articles, reduce the number per topic
                articles_per_topic = max(1, num_posts // len(topics))
        else:
            articles_per_topic = num_posts
        
        # Get the date range for the past 3 days
        today = datetime.now()
        three_days_ago = today - timedelta(days=3)
        from_date = three_days_ago.strftime('%Y-%m-%d')
        
        all_articles = []
        
        # Search for each topic
        for topic in topics:
            print(f"⏳ Searching for news about: {topic}...")
            
            # Construct the API URL
            base_url = "https://newsapi.org/v2/everything"
            params = {
                "q": topic,
                "from": from_date,
                "sortBy": "relevancy",
                "language": "en",
                "pageSize": articles_per_topic,
                "apiKey": news_api_key
            }
            
            try:
                # Make the API request
                response = requests.get(base_url, params=params)
                response.raise_for_status()  # Raise an exception for HTTP errors
                
                # Parse the response
                data = response.json()
                
                if data.get("status") == "ok" and data.get("articles"):
                    for article in data["articles"][:articles_per_topic]:
                        # Format the article data
                        formatted_article = {
                            "title": article.get("title", ""),
                            "source": article.get("source", {}).get("name", "Unknown"),
                            "date": article.get("publishedAt", "")[:10],  # Extract date part only
                            "url": article.get("url", ""),
                            "summary": article.get("description", ""),
                            "topic": topic
                        }
                        all_articles.append(formatted_article)
                else:
                    print(f"⚠️ No articles found for topic: {topic}")
            except Exception as e:
                print(f"⚠️ Error fetching news for topic {topic}: {str(e)}")
        
        # Limit to the requested number of posts if we already have enough
        if len(all_articles) >= num_posts:
            print(f"Limiting to {num_posts} articles as requested")
            return all_articles[:num_posts]
            
        # If we didn't get enough articles, search for trending topics
        if len(all_articles) < num_posts:
            print("⏳ Searching for trending business and technology topics...")
            trending_topics = ["business innovation", "workplace trends", "leadership", 
                             "industry disruption", "future of work", "digital transformation"]
            
            remaining = num_posts - len(all_articles)
            articles_per_trending = max(1, remaining // len(trending_topics))
            
            for topic in trending_topics:
                if len(all_articles) >= num_posts:
                    break
                    
                base_url = "https://newsapi.org/v2/everything"
                params = {
                    "q": topic,
                    "from": from_date,
                    "sortBy": "relevancy",
                    "language": "en",
                    "pageSize": articles_per_trending,
                    "apiKey": news_api_key
                }
                
                try:
                    response = requests.get(base_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("status") == "ok" and data.get("articles"):
                        for article in data["articles"][:articles_per_trending]:
                            formatted_article = {
                                "title": article.get("title", ""),
                                "source": article.get("source", {}).get("name", "Unknown"),
                                "date": article.get("publishedAt", "")[:10],
                                "url": article.get("url", ""),
                                "summary": article.get("description", ""),
                                "topic": topic
                            }
                            all_articles.append(formatted_article)
                except Exception as e:
                    print(f"⚠️ Error fetching trending news for {topic}: {str(e)}")
        
        # Ensure we don't exceed the requested number of posts
        if len(all_articles) > num_posts:
            print(f"Limiting to {num_posts} articles as requested")
            all_articles = all_articles[:num_posts]
            
        # Print summary of found articles
        print(f"✅ Found {len(all_articles)} news articles from {len(set(a.get('source') for a in all_articles))} different sources")
        for i, article in enumerate(all_articles, 1):
            print(f"  {i}. {article['title']} ({article['source']}) - Topic: {article.get('topic', 'None')}")
        
        # Ensure each article has a unique ID
        for i, article in enumerate(all_articles):
            article['id'] = f"article_{i+1}"
            
        return all_articles
        
    async def _fallback_search_tech_news(self, topics: List[str], num_posts: int = 5) -> List[Dict[str, str]]:
        """
        Fallback method to search for news using the OpenAI agent if News API key is not available.
        """
        # Get the date range for the past 3 days
        today = datetime.now()
        three_days_ago = today - timedelta(days=3)
        date_range = f"{three_days_ago.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}"
        
        # Calculate how many articles to request for each category
        tech_articles = max(num_posts // 2, 3)  # At least 3 tech articles
        trending_articles = num_posts - tech_articles  # Remaining for trending topics
        
        # Construct the search queries
        topics_str = ", ".join(topics) if topics else "technology, AI, software development, data science"
        
        # First query for technology news
        tech_query = f"Search for {tech_articles} important and interesting technology news from {date_range} about {topics_str}. Focus on stories that have practical applications or solve real problems. For each article, provide the title, source, publication date, URL, and a brief summary that explains why it matters."
        
        # Second query for trending topics across industries
        trending_query = f"Search for {trending_articles} trending topics or news stories from {date_range} that professionals are discussing on LinkedIn. Look beyond just technology to include business innovation, workplace trends, leadership insights, and industry disruptions. For each topic, provide the title, source, publication date, URL, and a brief summary that explains why it's relevant to professionals."
        
        # Run both queries and combine results
        print("⏳ Searching for technology news (using fallback method)...")
        tech_result = await Runner.run(self.news_searcher_agent, tech_query)
        tech_articles = self._parse_news_results(str(tech_result.final_output))
        
        print("⏳ Searching for trending professional topics (using fallback method)...")
        trending_result = await Runner.run(self.news_searcher_agent, trending_query)
        trending_articles = self._parse_news_results(str(trending_result.final_output))
        
        # Combine all articles
        all_articles = tech_articles + trending_articles
        
        # Limit to the requested number of posts
        if len(all_articles) > num_posts:
            print(f"Limiting to {num_posts} articles as requested")
            all_articles = all_articles[:num_posts]
            
        return all_articles

    def _parse_news_results(self, results_text: str) -> List[Dict[str, str]]:
        """Parse the news search results into structured data."""
        # This is a simplified implementation
        # In a real system, you would implement more robust parsing
        articles = []
        
        # Handle empty or invalid responses
        if not results_text or len(results_text.strip()) < 10:
            print("Warning: Received empty or invalid news results.")
            # Create a sample article for testing if no results are found
            sample_article = {
                'title': 'OpenAI Releases GPT-5 with Revolutionary Capabilities',
                'source': 'Tech News Daily',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'url': 'https://example.com/gpt5-release',
                'summary': 'OpenAI has released GPT-5, featuring unprecedented reasoning capabilities and multimodal understanding. The new model demonstrates significant improvements in coding, mathematical reasoning, and creative tasks.'  
            }
            articles.append(sample_article)
            return articles
        
        # More robust parsing logic with multiple formats supported
        current_article = {}
        lines = results_text.strip().split('\n')
        article_markers = ["Article", "News Item", "#", "---"]
        field_markers = {
            "title": ["Title:", "- Title:", "1. Title:", "TITLE:"],
            "source": ["Source:", "- Source:", "2. Source:", "SOURCE:", "Publication:", "Publisher:"],
            "date": ["Date:", "- Date:", "3. Date:", "DATE:", "Published:", "Publication Date:"],
            "url": ["URL:", "- URL:", "4. URL:", "Link:", "- Link:"],
            "summary": ["Summary:", "- Summary:", "5. Summary:", "Brief:", "Description:"]
        }
        
        # Check if we're starting a new article
        def is_article_marker(line):
            return any(line.startswith(marker) for marker in article_markers) or \
                   any(line.startswith(marker) for marker in field_markers["title"])
        
        # Process each line
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a new article marker
            if is_article_marker(line) and current_article and 'title' in current_article:
                articles.append(current_article)
                current_article = {}
            
            # Process each field
            field_found = False
            for field, markers in field_markers.items():
                for marker in markers:
                    if line.startswith(marker):
                        current_article[field] = line.split(marker, 1)[1].strip()
                        field_found = True
                        break
                if field_found:
                    break
            
            # If no field marker found and we have a summary, append to it
            if not field_found and 'summary' in current_article:
                current_article['summary'] += " " + line
        
        # Add the last article if it exists
        if current_article and 'title' in current_article:
            articles.append(current_article)
            
        # If we still have no articles, create a sample one
        if not articles:
            print("Warning: Could not parse any articles from the response. Creating sample article.")
            sample_article = {
                'title': 'AI Advances in Natural Language Processing',
                'source': 'AI Research Journal',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'url': 'https://example.com/ai-nlp-advances',
                'summary': 'Recent breakthroughs in natural language processing have enabled more human-like interactions with AI systems. These advances are being applied across industries from healthcare to customer service.'  
            }
            articles.append(sample_article)
        
        return articles

    async def _write_post_drafts(self, news_articles: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Generate LinkedIn post drafts based on news articles.
        
        Args:
            news_articles: List of news article dictionaries
            
        Returns:
            List of post draft dictionaries
        """
        post_drafts = []
        
        # Get persona information and preferences
        author_persona = self.user_preferences.get("linkedin_persona", "")
        author_persona_name = self.user_preferences.get("author_persona_name", "Default")
        target_audience = self.user_preferences.get("target_audience_persona", "")
        audience_persona_name = self.user_preferences.get("audience_persona_name", "Default")
        tone = self.user_preferences.get("tone", "professional and insightful")
        length = self.user_preferences.get("length", "2-3 paragraphs")
        hashtags = self.user_preferences.get("include_hashtags", True)
        
        for article in news_articles:
            # Construct the prompt for the post writer agent
            prompt = f"""
            Write a highly opinionated and conversational LinkedIn post about this news, keeping in mind both the author's persona and the target audience:
            
            AUTHOR PERSONA ({author_persona_name}):
            {author_persona}
            
            TARGET AUDIENCE ({audience_persona_name}):
            {target_audience}
            
            NEWS ARTICLE:
            Title: {article['title']}
            Source: {article.get('source', 'Unknown')}
            Date: {article.get('date', 'Recent')}
            Summary: {article.get('summary', '')}
            URL: {article.get('url', '')}
            
            Use a {tone} tone. The post should be {length} in length.
            {"Include 3-5 relevant hashtags at the end." if hashtags else "Do not include hashtags."}
            
            IMPORTANT GUIDELINES:
            1. Be HIGHLY OPINIONATED - take a clear stance and don't be afraid to be controversial
            2. Use a conversational, casual tone - avoid corporate speak and formality
            3. Write as if you're texting a friend about something that got you fired up
            4. Include your personal take and strong viewpoint on the topic
            5. Use first-person language (I think, I believe, In my experience)
            6. Be authentic and show your personality - let your unique voice shine through
            7. Challenge conventional thinking or offer a fresh perspective
            8. DO NOT use any emojis
            9. End with a provocative question that invites debate or discussion
            10. The post should sound authentic to the author persona but specifically crafted to appeal to the target audience
            """
            
            # Run the post writer agent
            result = await Runner.run(self.post_writer_agent, prompt)
            
            # Create the post draft
            post_draft = {
                "article": article,
                "content": str(result.final_output),
                "draft_id": f"draft_{len(post_drafts) + 1}"
            }
            
            post_drafts.append(post_draft)
        
        return post_drafts

    async def _edit_posts(self, post_drafts: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Edit and refine the post drafts.
        
        Args:
            post_drafts: List of post draft dictionaries
            
        Returns:
            List of edited post dictionaries with feedback
        """
        edited_posts = []
        
        # Get persona information
        author_persona = self.user_preferences.get("linkedin_persona", "")
        author_persona_name = self.user_preferences.get("author_persona_name", "Default")
        target_audience = self.user_preferences.get("target_audience_persona", "")
        audience_persona_name = self.user_preferences.get("audience_persona_name", "Default")
        branding = self.user_preferences.get("branding", "")
        messaging = self.user_preferences.get("key_messages", [])
        messaging_str = "\n".join([f"- {msg}" for msg in messaging]) if messaging else ""
        
        for draft in post_drafts:
            # Construct the prompt for the editor agent
            prompt = f"""
            Review and edit this LinkedIn post draft to make it MORE OPINIONATED and LESS FORMAL, while considering both the author's persona and the target audience:
            
            AUTHOR PERSONA ({author_persona_name}):
            {author_persona}
            
            TARGET AUDIENCE ({audience_persona_name}):
            {target_audience}
            
            POST DRAFT:
            {draft['content']}
            
            Please edit this post to:
            1. Make it MORE OPINIONATED - ensure it takes a clear stance and isn't afraid to be controversial
            2. Make it LESS FORMAL - use a conversational, casual tone that avoids corporate speak
            3. Enhance the personal voice - use more first-person language (I think, I believe, In my experience)
            4. Strengthen the viewpoint - make the author's perspective and opinions more prominent
            5. Challenge conventional thinking - add a fresh or provocative perspective
            6. Ensure it sounds authentic to the author's persona
            7. Make it resonate specifically with the target audience
            8. Incorporate these key messaging points where relevant:
            {messaging_str}
            9. End with a provocative question that invites debate or discussion
            
            Provide your edited version of the post, followed by specific feedback about what you changed and why.
            Focus on making the post more opinionated, less formal, and more authentic to the author's voice while still appealing to the target audience.
            """
            
            # Run the editor agent
            result = await Runner.run(self.editor_agent, prompt)
            
            # Parse the result to separate the edited post from the feedback
            edited_content, feedback = self._parse_editor_result(str(result.final_output))
            
            # Create the edited post
            edited_post = {
                "article": draft["article"],
                "original_content": draft["content"],
                "edited_content": edited_content,
                "feedback": feedback,
                "draft_id": draft["draft_id"]
            }
            
            edited_posts.append(edited_post)
        
        return edited_posts

    def _parse_editor_result(self, result_text: str) -> tuple[str, str]:
        """Parse the editor result to separate the edited post from the feedback."""
        # This is a simplified implementation
        # In a real system, you would implement more robust parsing
        
        # Try to find common separators
        separators = ["FEEDBACK:", "FEEDBACK", "EDITS:", "CHANGES:", "---", "***"]
        
        for separator in separators:
            if separator in result_text:
                parts = result_text.split(separator, 1)
                return parts[0].strip(), parts[1].strip()
        
        # If no separator is found, assume the first half is the post and the second half is feedback
        # This is a fallback and not ideal
        midpoint = len(result_text) // 2
        return result_text[:midpoint].strip(), result_text[midpoint:].strip()

    async def _revise_posts(self, edited_posts: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Revise posts based on editor feedback.
        
        Args:
            edited_posts: List of edited post dictionaries with feedback
            
        Returns:
            List of final post dictionaries
        """
        final_posts = []
        
        # Get persona information
        author_persona = self.user_preferences.get("linkedin_persona", "")
        author_persona_name = self.user_preferences.get("author_persona_name", "Default")
        target_audience = self.user_preferences.get("target_audience_persona", "")
        audience_persona_name = self.user_preferences.get("audience_persona_name", "Default")
        
        for post in edited_posts:
            # Construct the prompt for the reviser agent
            prompt = f"""
            Revise this LinkedIn post to make it EVEN MORE OPINIONATED and CONVERSATIONAL, based on the editor's feedback, while keeping in mind both the author's persona and the target audience:
            
            AUTHOR PERSONA ({author_persona_name}):
            {author_persona}
            
            TARGET AUDIENCE ({audience_persona_name}):
            {target_audience}
            
            ORIGINAL POST:
            {post['original_content']}
            
            EDITED POST:
            {post['edited_content']}
            
            EDITOR'S FEEDBACK:
            {post['feedback']}
            
            IMPORTANT GUIDELINES FOR FINAL REVISION:
            1. Make it HIGHLY OPINIONATED - ensure it takes a bold stance and isn't afraid to be controversial
            2. Keep it CONVERSATIONAL and INFORMAL - it should read like someone speaking naturally, not writing formally
            3. Emphasize the PERSONAL VOICE - use plenty of first-person language (I think, I believe, In my experience)
            4. Make sure the author's unique perspective and strong opinions shine through
            5. Avoid corporate jargon, buzzwords, and anything that sounds like marketing speak
            6. Ensure it sounds authentic to the author's persona while specifically appealing to the target audience
            7. End with a provocative question that will spark debate or discussion
            
            The final post should feel like a passionate, opinionated take from a real person with strong views, not a sanitized corporate message.
            """
            
            # Run the reviser agent
            result = await Runner.run(self.reviser_agent, prompt)
            
            # Create the final post
            final_post = {
                "article": post["article"],
                "content": str(result.final_output),
                "draft_id": post["draft_id"],
                "revision_history": {
                    "original": post["original_content"],
                    "edited": post["edited_content"],
                    "feedback": post["feedback"]
                }
            }
            
            final_posts.append(final_post)
        
        return final_posts

    async def _prepare_for_scheduling(self, final_posts: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Prepare posts for scheduling using the selected social media scheduler.
        
        Args:
            final_posts: List of final post dictionaries
            
        Returns:
            List of posts ready for scheduling with metadata
        """
        # Get the scheduler name from user preferences or default to "manual"
        scheduler_name = self.user_preferences.get("scheduler", "manual")
        
        scheduled_posts = []
        
        # Calculate posting times based on user preferences
        posting_times = self._calculate_posting_times(
            len(final_posts), 
            self.user_preferences.get("posting_frequency", "daily"),
            self.user_preferences.get("posting_time", "9:00 AM"),
            self.user_preferences.get("timezone", "America/Los_Angeles")
        )
        
        for i, post in enumerate(final_posts):
            scheduled_post = post.copy()
            scheduled_post["scheduling"] = {
                "platform": "LinkedIn",
                "scheduled_time": posting_times[i],
                "status": "ready_to_schedule",
                "scheduler": scheduler_name
            }
            
            scheduled_posts.append(scheduled_post)
        
        # If user has selected a scheduler other than manual, attempt to schedule the posts
        if scheduler_name.lower() != "manual":
            try:
                scheduler = self._get_scheduler(scheduler_name)
                scheduling_results = scheduler.schedule_batch(scheduled_posts)
                
                # Update posts with scheduling results
                for i, result in enumerate(scheduling_results):
                    if i < len(scheduled_posts):
                        scheduled_posts[i]["scheduling_result"] = result
                        
                        # Update status based on result
                        if result.get("status") == "error":
                            scheduled_posts[i]["scheduling"]["status"] = "error"
                            scheduled_posts[i]["scheduling"]["error"] = result.get("error")
                        else:
                            scheduled_posts[i]["scheduling"]["status"] = result.get("status", "scheduled")
            except Exception as e:
                print(f"Warning: Error scheduling posts: {str(e)}")
                print("Posts will need to be scheduled manually.")
                for post in scheduled_posts:
                    post["scheduling"]["status"] = "manual"
                    post["scheduling"]["error"] = str(e)
        
        return scheduled_posts

    def _calculate_posting_times(self, num_posts: int, frequency: str, time: str, timezone: str) -> List[str]:
        """Calculate posting times based on user preferences."""
        # This is a simplified implementation
        # In a real system, you would implement more sophisticated scheduling logic
        
        now = datetime.now()
        posting_times = []
        
        for i in range(num_posts):
            if frequency == "daily":
                post_date = now + timedelta(days=i)
            elif frequency == "weekdays_only":
                # Skip weekends
                days_to_add = i
                if (now.weekday() + i) % 7 >= 5:  # 5 and 6 are Saturday and Sunday
                    days_to_add += 2
                post_date = now + timedelta(days=days_to_add)
            else:  # Default to every other day
                post_date = now + timedelta(days=i*2)
            
            posting_times.append(f"{post_date.strftime('%Y-%m-%d')} {time} {timezone}")
        
        return posting_times
        
    def _get_scheduler(self, scheduler_name: str) -> SocialMediaScheduler:
        """Get the appropriate social media scheduler based on user preference."""
        from .buffer_integration import ManualScheduler
        
        scheduler_map = {
            "hootsuite": HootsuiteIntegration,
            "later": LatermediaIntegration,
            "linkedin": LinkedInDirectIntegration,
            "manual": ManualScheduler
        }
        
        scheduler_class = scheduler_map.get(scheduler_name.lower(), ManualScheduler)
        
        try:
            return scheduler_class()
        except ValueError as e:
            print(f"Warning: Could not initialize {scheduler_name} scheduler: {str(e)}")
            print("Falling back to manual scheduling mode (no API integration)")
            return ManualScheduler()
            
    def _extract_main_topic(self, post: Dict[str, Any]) -> str:
        """Extract the main topic from a post for use in filenames."""
        # Try to extract from the article title first
        if post.get("article") and post["article"].get("title"):
            title = post["article"]["title"]
            # Extract key terms from title
            key_terms = re.findall(r'\b(?:AI|ML|NLP|GPT|Blockchain|Crypto|Web3|Cloud|Data|Tech|Software|Hardware|IoT|AR|VR|XR|Quantum|Cyber|Security|DevOps|API|Mobile|App|SaaS|PaaS|IaaS|5G|Edge|Computing|Robotics)\b', title, re.IGNORECASE)
            if key_terms:
                return key_terms[0].lower()
            
            # If no key terms, take the first 2-3 significant words
            words = re.findall(r'\b[A-Za-z][A-Za-z]{2,}\b', title)
            if len(words) >= 2:
                return "-".join(words[:2]).lower()
        
        # If no article title or extraction failed, try to get from content
        if post.get("content"):
            # Look for hashtags
            hashtags = re.findall(r'#(\w+)', post["content"])
            if hashtags:
                return hashtags[0].lower()
            
            # If no hashtags, try to extract key tech terms
            key_terms = re.findall(r'\b(?:AI|ML|NLP|GPT|Blockchain|Crypto|Web3|Cloud|Data|Tech|Software|Hardware|IoT|AR|VR|XR|Quantum|Cyber|Security|DevOps|API|Mobile|App|SaaS|PaaS|IaaS|5G|Edge|Computing|Robotics)\b', post["content"], re.IGNORECASE)
            if key_terms:
                return key_terms[0].lower()
        
        # Default if nothing else works
        return f"tech-post-{post.get('draft_id', 'unknown')}"
        
    def _save_posts_as_files(self, posts: List[Dict[str, Any]], user_preferences: Dict[str, Any]) -> None:
        """Save each post as a separate markdown file with user, date, and topic in the filename."""
        # Create a directory for the posts if it doesn't exist
        output_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "generated_posts"
        output_dir.mkdir(exist_ok=True)
        
        # Get the username (default to 'user' if not provided)
        username = user_preferences.get("username", "user").lower().replace(" ", "-")
        
        # Get today's date for the filename
        today_date = datetime.now().strftime("%Y-%m-%d")
        
        print(f"\n✅ Saving {len(posts)} posts to {output_dir}...")
        print(f"Post details: {', '.join([post['article'].get('title', 'Untitled') for post in posts])}")
        
        # Save each post as a separate file
        for i, post in enumerate(posts):
            # Get the title or topic for the filename
            article_title = post['article'].get('title', '')
            article_topic = post['article'].get('topic', '')
            article_id = post['article'].get('id', f"post-{i+1}")
            
            # Prioritize using the topic if available, otherwise use the title
            if article_topic:
                filename_base = article_topic
            elif article_title:
                filename_base = article_title
            else:
                filename_base = f"topic-{i+1}"
                
            # Clean the filename base for use in a filename (keep it short)
            clean_title = filename_base.lower().replace(' ', '-')[:50].strip('-')
            
            # Add article ID to ensure uniqueness if multiple articles have the same topic/title
            # Create the filename: user_date_title_id.md
            filename = f"{username}_{today_date}_{clean_title}_{i+1}.md"
            file_path = output_dir / filename
            
            # Create the markdown content
            markdown_content = f"# LinkedIn Post: {post['article'].get('title', 'Tech Update')}\n\n"
            markdown_content += f"**Date Generated:** {today_date}\n\n"
            markdown_content += f"**Topic:** {post['article'].get('topic', filename_base)}\n\n"
            markdown_content += f"**Source:** {post['article'].get('source', 'Unknown')}\n\n"
            markdown_content += f"**Original URL:** {post['article'].get('url', '')}\n\n"
            markdown_content += f"**Recommended Posting Time:** {post.get('scheduling', {}).get('scheduled_time', post.get('recommended_posting_time', 'Any time'))}\n\n"
            markdown_content += f"## Post Content\n\n{post['content']}\n\n"
            
            # Add revision history if available
            if post.get("revision_history"):
                markdown_content += "## Revision History\n\n"
                markdown_content += "### Original Draft\n\n"
                markdown_content += f"{post['revision_history'].get('original', '')}\n\n"
                markdown_content += "### Editor Feedback\n\n"
                markdown_content += f"{post['revision_history'].get('feedback', '')}\n\n"
            
            # Write the file
            with open(file_path, "w") as f:
                f.write(markdown_content)
            
            print(f"  - Saved post {i+1} to {filename}")

    def _create_news_searcher_agent(self) -> Agent:
        """Create the agent responsible for searching technology news."""
        return Agent(
            name="Technology News Searcher",
            model="gpt-4-turbo",
            instructions="""
            You are a specialized technology news researcher. Your task is to find and summarize the most important and interesting technology news from the specified time period.
            
            For each news article you find, provide:
            - Title: The headline of the article
            - Source: The publication or website
            - Date: When it was published
            - URL: Link to the article
            - Summary: A concise 2-3 sentence summary of the key points
            
            Focus on high-quality sources and significant developments in technology, AI, software development, data science, and related fields.
            Prioritize news that would be interesting and relevant for a technology professional to share on LinkedIn.
            Ensure the information is accurate, recent, and properly attributed.
            """
        )

    def _create_post_writer_agent(self) -> Agent:
        """Create the agent responsible for writing LinkedIn post drafts."""
        return Agent(
            name="LinkedIn Post Writer",
            model="gpt-4-turbo",
            instructions="""
            You are a professional LinkedIn content writer specializing in creating authentic, story-driven posts. Your task is to create engaging LinkedIn posts based on news articles that avoid sounding like marketing or advertisements.
            
            CRITICAL GUIDELINES:
            1. NEVER WRITE MARKETING COPY: If your writing reads like marketing or an ad, start over. Readers will reject content that feels promotional and it will damage the author's credibility.
            
            2. FRAME AS A STORY: Structure content as a narrative: "we needed to do X so we tried Y, had trouble because of Z, solved it with W, and here are surprising details A, B, and C"
            
            3. ADDRESS THE "WHY SHOULD I CARE" QUESTIONS:
               - What is it? (explain clearly without jargon)
               - Why does it matter? (what pain does it solve)
               - What makes it challenging? (show the complexity)
            
            4. WRITE CONVERSATIONALLY: Write as if the author is meeting a friend for drinks who asks good questions about their work.
            
            5. NO EMOJIS: Do not include any emojis in your writing.
            
            6. BE AUTHENTIC: The post should sound like a real person sharing something they personally found interesting, not trying to manipulate readers.
            
            7. END WITH A GENUINE QUESTION: Conclude with a thoughtful question that invites real discussion, not a forced call-to-action.
            
            8. USE FORMATTING: Include appropriate line breaks for readability on LinkedIn.
            
            9. INCLUDE HASHTAGS ONLY WHEN REQUESTED: If requested, add 3-5 relevant hashtags at the end.
            
            Adapt your writing to match the requested tone and length while maintaining authenticity and a conversational style.
            """
        )

    def _create_editor_agent(self) -> Agent:
        """Create the agent responsible for editing and providing feedback on posts."""
        return Agent(
            name="LinkedIn Post Editor",
            model="gpt-4-turbo",
            instructions="""
            You are a professional content editor specializing in LinkedIn and social media content. Your task is to review and edit LinkedIn post drafts to improve their quality and effectiveness.
            
            Follow these critical guidelines when editing:
            
            1. AVOID MARKETING LANGUAGE: If the post reads like marketing or an ad, rewrite it completely. Readers will reject content that feels like an ad, and it will damage the author's credibility.
            
            2. FRAME AS A STORY: Transform the content into a narrative structure: "we needed to do X so we tried Y, had trouble because of Z, solved it with W, and here are surprising details A, B, and C"
            
            3. CLEAR THE "WHY SHOULD I CARE" HURDLES:
               - Who are you? (establish credibility naturally)
               - Why is this interesting? (explain the real-world impact)
               - What is it? (explain clearly without jargon)
               - Why does it matter? (what pain does it solve)
               - What makes it challenging? (show the complexity)
            
            4. WRITE CONVERSATIONALLY: Edit as if the author is meeting a friend for drinks who asks good questions about their work.
            
            5. REMOVE ALL EMOJIS: Do not include any emojis in your edits.
            
            6. CHECK FOR TECHNICAL ACCURACY: Ensure the content is factually correct and the logic is sound.
            
            7. MAINTAIN AUTHENTICITY: The post should sound like a real person sharing something they personally found interesting, not trying to manipulate readers.
            
            Provide your edited version of the post, followed by specific feedback explaining what you changed and why.
            Your feedback should be constructive, specific, and actionable.
            """
        )

    def _create_reviser_agent(self) -> Agent:
        """Create the agent responsible for revising posts based on editor feedback."""
        return Agent(
            name="LinkedIn Post Reviser",
            model="gpt-4-turbo",
            instructions="""
            You are a professional content reviser specializing in finalizing LinkedIn posts. Your task is to create the final version of LinkedIn posts by incorporating editor feedback while ensuring the content remains authentic and non-promotional.
            
            CRITICAL GUIDELINES:
            1. NEVER ALLOW MARKETING LANGUAGE: If any part of the post still reads like marketing or an ad after the editor's changes, rewrite it completely. Readers will reject content that feels promotional.
            
            2. MAINTAIN THE STORY STRUCTURE: Ensure the post follows a narrative flow that feels like a real person sharing an experience or insight.
            
            3. ENSURE THE "WHY SHOULD I CARE" QUESTIONS ARE ANSWERED:
               - What is it? (explained clearly without jargon)
               - Why does it matter? (what pain does it solve)
               - What makes it challenging? (showing the complexity)
            
            4. PRESERVE CONVERSATIONAL TONE: The post should read as if the author is talking to a friend, not addressing an audience or market.
            
            5. REMOVE ALL EMOJIS: Ensure there are no emojis in the final version.
            
            6. VERIFY AUTHENTICITY: The post must sound like a real person sharing something they personally found interesting, not trying to manipulate readers.
            
            7. CHECK THE CLOSING QUESTION: Ensure it invites genuine discussion rather than serving as a marketing call-to-action.
            
            8. OPTIMIZE FORMATTING: Ensure appropriate line breaks and formatting for LinkedIn readability.
            
            9. HANDLE HASHTAGS APPROPRIATELY: Include hashtags only if requested in the original instructions, and ensure they are relevant and properly formatted.
            
            Your goal is to produce a final version that is authentic, engaging, and represents the user's genuine professional voice on LinkedIn.
            """
        )
