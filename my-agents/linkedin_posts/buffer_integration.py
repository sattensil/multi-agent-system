import os
import json
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class SocialMediaScheduler:
    """Base class for social media scheduling integrations."""
    
    def schedule_linkedin_post(self, post_content: str, scheduled_time: Optional[str] = None) -> Dict[str, Any]:
        """Schedule a post to LinkedIn."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def schedule_batch(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Schedule a batch of posts."""
        raise NotImplementedError("Subclasses must implement this method")


class HootsuiteIntegration(SocialMediaScheduler):
    """Integration with Hootsuite for scheduling LinkedIn posts."""
    
    BASE_URL = "https://platform.hootsuite.com/v1"
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize the Hootsuite integration.
        
        Args:
            access_token: Hootsuite API access token. If None, will try to get from environment.
        """
        self.access_token = access_token or os.getenv("HOOTSUITE_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError("Hootsuite access token is required. Set HOOTSUITE_ACCESS_TOKEN in your .env file.")
    
    def get_social_profiles(self) -> List[Dict[str, Any]]:
        """
        Get all social media profiles connected to the Hootsuite account.
        
        Returns:
            List of profile dictionaries
        """
        endpoint = f"{self.BASE_URL}/socialProfiles"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        
        return response.json().get("data", [])
    
    def get_linkedin_profile_id(self) -> Optional[str]:
        """
        Get the LinkedIn profile ID from the connected Hootsuite account.
        
        Returns:
            LinkedIn profile ID or None if not found
        """
        profiles = self.get_social_profiles()
        
        for profile in profiles:
            if profile.get("type") == "LINKEDIN":
                return profile.get("id")
        
        return None
    
    def create_message(self, text: str, social_profile_ids: List[str], scheduled_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a scheduled message in Hootsuite.
        
        Args:
            text: Content of the post
            social_profile_ids: List of Hootsuite social profile IDs to post to
            scheduled_time: ISO 8601 timestamp for when to post. If None, will be sent immediately.
            
        Returns:
            Response from Hootsuite API
        """
        endpoint = f"{self.BASE_URL}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "text": text,
            "socialProfileIds": social_profile_ids
        }
        
        if scheduled_time:
            data["scheduledSendTime"] = scheduled_time
        
        response = requests.post(endpoint, headers=headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    def schedule_linkedin_post(self, post_content: str, scheduled_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Schedule a post to LinkedIn via Hootsuite.
        
        Args:
            post_content: Content of the LinkedIn post
            scheduled_time: When to schedule the post (optional)
            
        Returns:
            Response from Hootsuite API
        """
        # Get LinkedIn profile ID
        linkedin_profile_id = self.get_linkedin_profile_id()
        if not linkedin_profile_id:
            raise ValueError("No LinkedIn profile connected to Hootsuite account")
        
        # Convert scheduled_time to ISO 8601 if provided
        iso_time = None
        if scheduled_time:
            try:
                # Parse the scheduled time (format: "YYYY-MM-DD HH:MM timezone")
                parts = scheduled_time.split()
                date_str = parts[0]
                time_str = parts[1]
                # We're ignoring timezone for simplicity, but in a real app you'd handle it
                
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                iso_time = dt.isoformat() + "Z"  # Hootsuite requires UTC time with Z suffix
            except (ValueError, IndexError):
                print(f"Warning: Could not parse scheduled time '{scheduled_time}', posting immediately instead")
        
        # Schedule the post
        return self.create_message(post_content, [linkedin_profile_id], iso_time)
    
    def schedule_batch(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Schedule a batch of posts to Hootsuite.
        
        Args:
            posts: List of post dictionaries with 'content' and 'scheduling' keys
            
        Returns:
            List of Hootsuite API responses
        """
        results = []
        
        for post in posts:
            content = post.get("content", "")
            scheduled_time = post.get("scheduling", {}).get("scheduled_time")
            
            try:
                result = self.schedule_linkedin_post(content, scheduled_time)
                results.append({
                    "post_id": post.get("draft_id"),
                    "hootsuite_response": result,
                    "status": "scheduled",
                    "error": None
                })
            except Exception as e:
                results.append({
                    "post_id": post.get("draft_id"),
                    "hootsuite_response": None,
                    "status": "error",
                    "error": str(e)
                })
        
        return results


class LatermediaIntegration(SocialMediaScheduler):
    """Integration with Later (formerly Latermedia) for scheduling LinkedIn posts."""
    
    BASE_URL = "https://app.later.com/api/v2"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Later integration.
        
        Args:
            api_key: Later API key. If None, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("LATER_API_KEY")
        if not self.api_key:
            raise ValueError("Later API key is required. Set LATER_API_KEY in your .env file.")
    
    def get_profiles(self) -> List[Dict[str, Any]]:
        """
        Get all social media profiles connected to the Later account.
        
        Returns:
            List of profile dictionaries
        """
        endpoint = f"{self.BASE_URL}/profiles"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        
        return response.json().get("data", [])
    
    def get_linkedin_profile_id(self) -> Optional[str]:
        """
        Get the LinkedIn profile ID from the connected Later account.
        
        Returns:
            LinkedIn profile ID or None if not found
        """
        profiles = self.get_profiles()
        
        for profile in profiles:
            if profile.get("platform") == "linkedin":
                return profile.get("id")
        
        return None
    
    def create_post(self, profile_id: str, text: str, scheduled_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a scheduled post in Later.
        
        Args:
            profile_id: Later profile ID to post to
            text: Content of the post
            scheduled_time: ISO 8601 timestamp for when to post. If None, will be added to queue.
            
        Returns:
            Response from Later API
        """
        endpoint = f"{self.BASE_URL}/posts"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "profile_id": profile_id,
            "content": {
                "text": text
            }
        }
        
        if scheduled_time:
            data["scheduled_at"] = scheduled_time
        
        response = requests.post(endpoint, headers=headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    def schedule_linkedin_post(self, post_content: str, scheduled_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Schedule a post to LinkedIn via Later.
        
        Args:
            post_content: Content of the LinkedIn post
            scheduled_time: When to schedule the post (optional)
            
        Returns:
            Response from Later API
        """
        # Get LinkedIn profile ID
        linkedin_profile_id = self.get_linkedin_profile_id()
        if not linkedin_profile_id:
            raise ValueError("No LinkedIn profile connected to Later account")
        
        # Convert scheduled_time to ISO 8601 if provided
        iso_time = None
        if scheduled_time:
            try:
                # Parse the scheduled time (format: "YYYY-MM-DD HH:MM timezone")
                parts = scheduled_time.split()
                date_str = parts[0]
                time_str = parts[1]
                
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                iso_time = dt.isoformat()
            except (ValueError, IndexError):
                print(f"Warning: Could not parse scheduled time '{scheduled_time}', using Later's queue instead")
        
        # Schedule the post
        return self.create_post(linkedin_profile_id, post_content, iso_time)
    
    def schedule_batch(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Schedule a batch of posts to Later.
        
        Args:
            posts: List of post dictionaries with 'content' and 'scheduling' keys
            
        Returns:
            List of Later API responses
        """
        results = []
        
        for post in posts:
            content = post.get("content", "")
            scheduled_time = post.get("scheduling", {}).get("scheduled_time")
            
            try:
                result = self.schedule_linkedin_post(content, scheduled_time)
                results.append({
                    "post_id": post.get("draft_id"),
                    "later_response": result,
                    "status": "scheduled",
                    "error": None
                })
            except Exception as e:
                results.append({
                    "post_id": post.get("draft_id"),
                    "later_response": None,
                    "status": "error",
                    "error": str(e)
                })
        
        return results


class LinkedInDirectIntegration(SocialMediaScheduler):
    """Direct integration with LinkedIn's API for posting content."""
    
    BASE_URL = "https://api.linkedin.com/v2"
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize the LinkedIn direct integration.
        
        Args:
            access_token: LinkedIn API access token. If None, will try to get from environment.
        """
        self.access_token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError("LinkedIn access token is required. Set LINKEDIN_ACCESS_TOKEN in your .env file.")
    
    def get_current_user(self) -> Dict[str, Any]:
        """
        Get the current LinkedIn user profile.
        
        Returns:
            User profile dictionary
        """
        endpoint = f"{self.BASE_URL}/me"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def create_text_post(self, author: str, text: str) -> Dict[str, Any]:
        """
        Create a text post on LinkedIn.
        
        Args:
            author: LinkedIn URN for the author (person or organization)
            text: Content of the post
            
        Returns:
            Response from LinkedIn API
        """
        endpoint = f"{self.BASE_URL}/ugcPosts"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        data = {
            "author": f"urn:li:person:{author}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        response = requests.post(endpoint, headers=headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    def schedule_linkedin_post(self, post_content: str, scheduled_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Post content directly to LinkedIn.
        Note: LinkedIn's API doesn't support scheduling, so posts are published immediately.
        
        Args:
            post_content: Content of the LinkedIn post
            scheduled_time: Ignored as LinkedIn API doesn't support scheduling
            
        Returns:
            Response from LinkedIn API
        """
        if scheduled_time:
            print("Warning: LinkedIn API doesn't support scheduling. The post will be published immediately.")
        
        # Get user ID
        user = self.get_current_user()
        user_id = user.get("id")
        
        if not user_id:
            raise ValueError("Could not determine LinkedIn user ID")
        
        # Create the post
        return self.create_text_post(user_id, post_content)
    
    def schedule_batch(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Post a batch of content directly to LinkedIn.
        
        Args:
            posts: List of post dictionaries with 'content' and 'scheduling' keys
            
        Returns:
            List of LinkedIn API responses
        """
        results = []
        
        for post in posts:
            content = post.get("content", "")
            
            try:
                result = self.schedule_linkedin_post(content)
                results.append({
                    "post_id": post.get("draft_id"),
                    "linkedin_response": result,
                    "status": "published",  # Not scheduled, but published immediately
                    "error": None
                })
            except Exception as e:
                results.append({
                    "post_id": post.get("draft_id"),
                    "linkedin_response": None,
                    "status": "error",
                    "error": str(e)
                })
        
        return results
