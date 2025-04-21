#!/usr/bin/env python
"""
Simple Document Translator with Readability Testing

This script implements a straightforward workflow for document translation with readability testing:
1. Load an English document
2. Ask for the target language
3. Translate the document
4. Test readability
5. Revise if needed based on readability score
"""

import os
import sys
from typing import Dict, List, Optional, Union, Any
from enum import Enum

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables
# Try to load from current directory, then from parent directory
if not load_dotenv():
    # Try to load from parent directory
    parent_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(parent_env)

class TranslationState(str, Enum):
    """States in the translation workflow."""
    WAITING_FOR_DOCUMENT = "waiting_for_document"
    WAITING_FOR_LANGUAGE = "waiting_for_language"
    TRANSLATING = "translating"
    TESTING_READABILITY = "testing_readability"
    REVISING = "revising"
    COMPLETED = "completed"

class DocumentTranslator:
    """Document translator with readability testing."""
    
    def __init__(self):
        """Initialize the translator."""
        self.document_content = None
        self.target_language = None
        self.translated_content = None
        self.readability_score = None
        self.revision_needed = False
        self.current_state = TranslationState.WAITING_FOR_DOCUMENT
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    
    def process_document_input(self, document_input: str) -> str:
        """Process document input from user."""
        # Try to load from file if it looks like a file path
        if document_input.strip().endswith(('.txt', '.md', '.html')):
            try:
                with open(document_input.strip(), 'r', encoding='utf-8') as file:
                    self.document_content = file.read()
                    self.current_state = TranslationState.WAITING_FOR_LANGUAGE
                    return f"Document loaded successfully. Content preview:\n\n{self.document_content[:200]}...\n\nPlease specify the target language for translation."
            except FileNotFoundError:
                return "File not found. Please provide the document content directly."
        
        # Otherwise, treat the input as the document content
        self.document_content = document_input
        self.current_state = TranslationState.WAITING_FOR_LANGUAGE
        return f"Document content received. Content preview:\n\n{self.document_content[:200]}...\n\nPlease specify the target language for translation."
    
    def process_language_input(self, language_input: str) -> str:
        """Process target language input from user."""
        self.target_language = language_input.strip()
        self.current_state = TranslationState.TRANSLATING
        return f"Target language set to: {self.target_language}. Starting translation process..."
    
    def translate_document(self) -> str:
        """Translate the document to the target language."""
        if not self.document_content or not self.target_language:
            return "Missing document content or target language. Please provide both."
        
        llm = ChatOpenAI(model="gpt-4.1", temperature=0.2)
        
        system_prompt = f"""
        You are a professional translator. Translate the following document from English to {self.target_language}.
        Maintain the original formatting, tone, and intent of the document.
        Ensure the translation is natural and fluent in the target language.
        """
        
        translation_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=self.document_content)
        ]
        
        response = llm.invoke(translation_messages)
        self.translated_content = response.content
        self.current_state = TranslationState.TESTING_READABILITY
        
        return f"Translation completed. Preview:\n\n{self.translated_content[:200]}...\n\nNow testing readability..."
    
    def test_readability(self) -> str:
        """Test the readability of the translated content."""
        if not self.translated_content:
            return "No translated content to test for readability."
        
        llm = ChatOpenAI(model="gpt-4.1", temperature=0)
        
        system_prompt = f"""
        You are a readability expert for {self.target_language}. 
        Analyze the provided translated text and rate its readability on a scale from 1 to 10, 
        where 1 is very difficult to read and 10 is very easy to read.
        
        Consider factors such as:
        - Sentence complexity
        - Word choice (common vs. rare words)
        - Sentence length
        - Overall flow and coherence
        
        Provide a numerical score and a brief explanation of your assessment.
        Format your response as:
        SCORE: [numerical score]
        ASSESSMENT: [your explanation]
        """
        
        readability_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=self.translated_content)
        ]
        
        response = llm.invoke(readability_messages)
        assessment = response.content
        
        # Extract score from the response
        try:
            score_line = [line for line in assessment.split('\n') if line.startswith('SCORE:')][0]
            self.readability_score = float(score_line.replace('SCORE:', '').strip())
        except (IndexError, ValueError):
            self.readability_score = 5.0  # Default middle score if parsing fails
        
        self.revision_needed = self.readability_score < 7.0  # Threshold for revision
        
        if self.revision_needed:
            self.current_state = TranslationState.REVISING
            return f"Readability assessment:\n\n{assessment}\n\nThe readability score is {self.readability_score}/10, which is below our threshold of 7/10. Revising the translation for better readability..."
        else:
            self.current_state = TranslationState.COMPLETED
            return f"Readability assessment:\n\n{assessment}\n\nThe readability score is {self.readability_score}/10, which meets our standards. Translation is complete!"
    
    def revise_translation(self) -> str:
        """Revise the translation based on readability feedback."""
        if not self.revision_needed:
            self.current_state = TranslationState.COMPLETED
            return "No revision needed. The translation has good readability."
        
        llm = ChatOpenAI(model="gpt-4.1", temperature=0.3)
        
        system_prompt = f"""
        You are a professional translator and editor for {self.target_language}.
        The following translated text has a readability score of {self.readability_score}/10, 
        which indicates it needs improvement.
        
        Revise the translation to improve its readability while maintaining the original meaning.
        Focus on:
        - Simplifying complex sentences
        - Using more common vocabulary where appropriate
        - Improving flow and coherence
        - Maintaining the original tone and intent
        
        Provide the revised translation only.
        """
        
        revision_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=self.translated_content)
        ]
        
        response = llm.invoke(revision_messages)
        self.translated_content = response.content  # Update with revised content
        self.revision_needed = False  # Mark as revised
        self.current_state = TranslationState.TESTING_READABILITY  # Test the readability again
        
        return f"Translation revised for better readability. Preview:\n\n{self.translated_content[:200]}...\n\nTesting readability of revised translation..."
    
    def process_input(self, user_input: str) -> str:
        """Process user input based on current state."""
        if self.current_state == TranslationState.WAITING_FOR_DOCUMENT:
            return self.process_document_input(user_input)
        elif self.current_state == TranslationState.WAITING_FOR_LANGUAGE:
            return self.process_language_input(user_input)
        elif self.current_state == TranslationState.TRANSLATING:
            return self.translate_document()
        elif self.current_state == TranslationState.TESTING_READABILITY:
            return self.test_readability()
        elif self.current_state == TranslationState.REVISING:
            return self.revise_translation()
        else:
            return "Translation process is complete. You can start a new translation."
    
    def get_translation_result(self) -> Dict:
        """Get the final translation result."""
        return {
            "target_language": self.target_language,
            "translated_content": self.translated_content,
            "readability_score": self.readability_score,
            "revisions_made": self.revision_needed,
        }
    
    def is_completed(self) -> bool:
        """Check if the translation process is completed."""
        return self.current_state == TranslationState.COMPLETED

def save_translation(translation_data: Dict, output_file: str) -> None:
    """Save the translation to a file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(translation_data["translated_content"])
    
    # Save metadata to a JSON file
    import json
    metadata_file = f"{os.path.splitext(output_file)[0]}_metadata.json"
    metadata = {
        "target_language": translation_data["target_language"],
        "readability_score": translation_data["readability_score"],
        "revisions_made": translation_data["revisions_made"],
    }
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Translation saved to: {output_file}")
    print(f"Metadata saved to: {metadata_file}")

def run_interactive_translation():
    """Run the translation workflow interactively."""
    translator = DocumentTranslator()
    
    print("Document Translator with Readability Testing")
    print("===========================================")
    print("This tool will help you translate documents from English to any language")
    print("and ensure they have good readability in the target language.\n")
    
    # Initial prompt
    print("Assistant: Please provide the document content or a path to a text file.")
    
    while True:
        # Get user input
        user_input = input("\nYou: ")
        
        # Check for exit command
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("Exiting translation process.")
            break
        
        # Process the input
        response = translator.process_input(user_input)
        print(f"\nAssistant: {response}")
        
        # If we're in a processing state, continue automatically
        while translator.current_state in [TranslationState.TRANSLATING, TranslationState.TESTING_READABILITY, TranslationState.REVISING]:
            response = translator.process_input("")
            print(f"\nAssistant: {response}")
        
        # Check if we've reached the end
        if translator.is_completed():
            # Get the final translation
            final_translation = translator.get_translation_result()
            
            # Ask if the user wants to save the translation
            save_option = input("\nDo you want to save the translation? (y/n): ").strip().lower()
            if save_option == 'y':
                output_file = input("Enter output filename: ").strip()
                save_translation(final_translation, output_file)
            
            print("\nTranslation process completed!")
            break

def run_batch_translation(input_file: str, target_language: str, output_file: Optional[str] = None):
    """Run the translation workflow in batch mode."""
    translator = DocumentTranslator()
    
    # Set default output file if not provided
    if not output_file:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_{target_language}.txt"
    
    print(f"Translating '{input_file}' to {target_language}...")
    
    # Process document
    translator.process_input(input_file)
    
    # Set language
    translator.process_input(target_language)
    
    # Run the translation process
    while not translator.is_completed():
        translator.process_input("")
    
    # Get the final translation
    final_translation = translator.get_translation_result()
    
    # Save the translation
    save_translation(final_translation, output_file)
    
    print(f"Readability score: {final_translation['readability_score']}/10")
    if final_translation.get("revisions_made"):
        print("Note: The translation was revised to improve readability.")

def main():
    """Main function to parse arguments and run the appropriate mode."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Document Translator with Readability Testing")
    parser.add_argument("--input", "-i", help="Input file path (for batch mode)")
    parser.add_argument("--language", "-l", help="Target language (for batch mode)")
    parser.add_argument("--output", "-o", help="Output file path (for batch mode, optional)")
    
    args = parser.parse_args()
    
    # Check if we're in batch mode
    if args.input and args.language:
        run_batch_translation(args.input, args.language, args.output)
    else:
        # Interactive mode
        run_interactive_translation()

if __name__ == "__main__":
    main()
