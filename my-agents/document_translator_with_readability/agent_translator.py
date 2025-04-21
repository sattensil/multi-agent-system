#!/usr/bin/env python
"""
Multi-Agent Document Translator with Readability Testing

This script implements a document translation workflow using a supervisor-agent architecture:
1. Load an English document
2. Translate the document using a specialized translation agent
3. Test readability using a readability assessment agent
4. Revise if needed using a revision agent
5. Return the final translation

The workflow is coordinated by a supervisor agent that decides which agent to call next.
"""

import os
import sys
import json
from typing import Dict, List, Optional, Union, Any, Literal, TypedDict
from enum import Enum
from typing_extensions import Annotated

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command

# Load environment variables
# Try to load from current directory, then from parent directory
if not load_dotenv():
    # Try to load from parent directory
    parent_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(parent_env)

# Define the state schema for our workflow
class State(MessagesState):
    """State for the translation workflow."""
    document_content: Optional[str] = None
    target_language: Optional[str] = None
    translated_content: Optional[str] = None
    readability_score: Optional[float] = None
    revision_needed: bool = False
    next: str = "supervisor"

# Define the router for the supervisor agent
class Router(TypedDict):
    """Router schema for the supervisor agent."""
    next: Literal["translator", "readability_tester", "reviser", "FINISH"]
    reason: str

# System prompts for each agent
SUPERVISOR_PROMPT = """
You are a supervisor agent coordinating a document translation workflow. 
Your job is to decide which agent to call next based on the current state of the translation process.

The workflow has the following steps:
1. Translator agent: Translates the document from English to the target language
2. Readability tester agent: Tests the readability of the translated content
3. Reviser agent: Revises the translation if the readability score is below 7/10
4. FINISH: Completes the workflow when the translation is done and has good readability

Available agents:
- "translator": Translates the document from English to the target language
- "readability_tester": Tests the readability of the translated content
- "reviser": Revises the translation based on readability feedback
- "FINISH": Complete the workflow

Rules:
- Start with the translator if we have both document content and target language
- After translation, always test readability
- If readability score is below 7/10, call the reviser
- After revision, test readability again
- If readability score is 7 or higher, finish the workflow
- If we don't have document content or target language, finish with an error message
"""

TRANSLATOR_PROMPT = """
You are a professional translator. Your job is to translate documents from English to the specified target language.
Maintain the original formatting, tone, and intent of the document.
Ensure the translation is natural and fluent in the target language.
"""

READABILITY_TESTER_PROMPT = """
You are a readability assessment specialist for translated content. Your job is to evaluate the readability of translated text.

Assess the following aspects of the translation:
1. Clarity: Is the text easy to understand?
2. Fluency: Does the text flow naturally in the target language?
3. Appropriateness: Is the vocabulary and style appropriate for the content?
4. Consistency: Is terminology used consistently?
5. Cultural adaptation: Are cultural references properly adapted?

Rate the overall readability on a scale of 1-10, where:
1-3: Poor readability, major issues
4-6: Moderate readability, needs improvement
7-8: Good readability, minor issues
9-10: Excellent readability, no significant issues

Provide specific feedback on what aspects need improvement.
"""

REVISER_PROMPT = """
You are a professional translator and editor. Your job is to revise translations to improve their readability.

Focus on the following aspects:
1. Clarity: Make the text easier to understand
2. Fluency: Ensure the text flows naturally in the target language
3. Appropriateness: Use vocabulary and style appropriate for the content
4. Consistency: Use terminology consistently
5. Cultural adaptation: Properly adapt cultural references

Use the readability feedback to guide your revisions. Maintain the original meaning and intent of the text.
"""

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4.1", temperature=0.2)

# Define the agent nodes
def supervisor_node(state: State) -> Command[Literal["translator", "readability_tester", "reviser", END]]:
    """Supervisor agent that decides which agent to call next."""
    messages = [
        SystemMessage(content=SUPERVISOR_PROMPT),
    ] + state["messages"]
    
    # Add state information to the last message
    state_info = f"""
    Current state:
    - Document content: {"Available" if state.get("document_content") else "Not available"}
    - Target language: {state.get("target_language") or "Not specified"}
    - Translated content: {"Available" if state.get("translated_content") else "Not available"}
    - Readability score: {state.get("readability_score") or "Not assessed"}
    - Revision needed: {state.get("revision_needed")}
    """
    
    # Add state info to the last message if it exists
    if state["messages"]:
        last_message = state["messages"][-1]
        if isinstance(last_message, HumanMessage):
            combined_content = f"{last_message.content}\n\n{state_info}"
            state["messages"][-1] = HumanMessage(content=combined_content)
        else:
            state["messages"].append(HumanMessage(content=state_info))
    else:
        state["messages"].append(HumanMessage(content=state_info))
    
    response = llm.with_structured_output(Router).invoke(state["messages"])
    goto = response["next"]
    reason = response["reason"]
    
    # Add the supervisor's decision to the messages
    state["messages"].append(AIMessage(content=f"I've decided to call the {goto} agent. Reason: {reason}"))
    
    if goto == "FINISH":
        state["messages"].append(AIMessage(content="Translation process completed successfully."))
        return Command(goto=END, update={"next": "FINISH"})
    
    return Command(goto=goto, update={"next": goto})

def translator_node(state: State) -> State:
    """Translator agent that translates the document."""
    document_content = state.get("document_content")
    target_language = state.get("target_language")
    
    if not document_content or not target_language:
        state["messages"].append(AIMessage(content="Error: Missing document content or target language."))
        return state
    
    system_prompt = f"""
    {TRANSLATOR_PROMPT}
    
    Translate the following document from English to {target_language}.
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=document_content)
    ]
    
    response = llm.invoke(messages)
    translated_content = response.content
    
    state["translated_content"] = translated_content
    state["messages"].append(AIMessage(content=f"I've translated the document to {target_language}. Here's a preview:\n\n{translated_content[:200]}..."))
    
    return state

def readability_tester_node(state: State) -> State:
    """Readability tester agent that assesses the readability of the translation."""
    translated_content = state.get("translated_content")
    target_language = state.get("target_language")
    
    if not translated_content or not target_language:
        state["messages"].append(AIMessage(content="Error: Missing translated content or target language."))
        return state
    
    system_prompt = f"""
    {READABILITY_TESTER_PROMPT}
    
    Assess the readability of the following {target_language} text.
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=translated_content)
    ]
    
    response = llm.invoke(messages)
    feedback = response.content
    
    # Extract the readability score from the feedback
    import re
    score_match = re.search(r'(\d+(\.\d+)?)/10', feedback)
    if score_match:
        readability_score = float(score_match.group(1))
    else:
        # If no score is found, try to extract just a number
        score_match = re.search(r'(?:score|rating|grade):\s*(\d+(\.\d+)?)', feedback.lower())
        if score_match:
            readability_score = float(score_match.group(1))
        else:
            # Default to a moderate score if we can't extract one
            readability_score = 5.0
    
    state["readability_score"] = readability_score
    state["revision_needed"] = readability_score < 7.0
    
    state["messages"].append(AIMessage(content=f"I've assessed the readability of the translation. Score: {readability_score}/10\n\nFeedback: {feedback}"))
    
    return state

def reviser_node(state: State) -> State:
    """Reviser agent that improves the translation based on readability feedback."""
    translated_content = state.get("translated_content")
    target_language = state.get("target_language")
    readability_score = state.get("readability_score")
    
    if not translated_content or not target_language or readability_score is None:
        state["messages"].append(AIMessage(content="Error: Missing translated content, target language, or readability score."))
        return state
    
    # Get the last message which should contain the readability feedback
    feedback = ""
    for message in reversed(state["messages"]):
        if "I've assessed the readability" in message.content:
            feedback = message.content
            break
    
    system_prompt = f"""
    {REVISER_PROMPT}
    
    Revise the following {target_language} translation to improve its readability.
    The current readability score is {readability_score}/10.
    
    Feedback on the current translation:
    {feedback}
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=translated_content)
    ]
    
    response = llm.invoke(messages)
    revised_content = response.content
    
    state["translated_content"] = revised_content
    state["messages"].append(AIMessage(content=f"I've revised the translation to improve readability. Here's a preview:\n\n{revised_content[:200]}..."))
    
    return state

# Create the workflow graph
def create_translation_graph():
    """Create the translation workflow graph."""
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("translator", translator_node)
    workflow.add_node("readability_tester", readability_tester_node)
    workflow.add_node("reviser", reviser_node)
    
    # Add edges
    workflow.add_edge(START, "supervisor")
    workflow.add_edge("translator", "supervisor")
    workflow.add_edge("readability_tester", "supervisor")
    workflow.add_edge("reviser", "supervisor")
    
    # Compile the graph
    return workflow.compile()

def save_translation(translation_data: Dict, output_file: str) -> None:
    """Save the translation to a file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(translation_data["translated_content"])
    
    # Save metadata to a JSON file
    metadata_file = f"{os.path.splitext(output_file)[0]}_metadata.json"
    metadata = {
        "target_language": translation_data["target_language"],
        "readability_score": translation_data["readability_score"],
        "revisions_made": translation_data["revision_needed"],
    }
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Translation saved to: {output_file}")
    print(f"Metadata saved to: {metadata_file}")

def run_interactive_translation():
    """Run the translation workflow interactively."""
    # Create the workflow graph
    translation_graph = create_translation_graph()
    
    print("Multi-Agent Document Translator with Readability Testing")
    print("======================================================")
    print("This tool will help you translate documents from English to any language")
    print("and ensure they have good readability in the target language.\n")
    
    # Initial state
    state = {"messages": []}
    
    # Get document content
    print("Assistant: Please provide the document content or a path to a text file.")
    document_input = input("\nYou: ")
    
    # Check for exit command
    if document_input.lower() in ['exit', 'quit', 'q']:
        print("Exiting translation process.")
        return
    
    # Try to load from file if it looks like a file path
    if document_input.strip().endswith(('.txt', '.md', '.html')):
        try:
            with open(document_input.strip(), 'r', encoding='utf-8') as file:
                document_content = file.read()
                print(f"\nAssistant: Document loaded successfully. Content preview:\n\n{document_content[:200]}...\n")
        except FileNotFoundError:
            print("\nAssistant: File not found. Please provide the document content directly.")
            document_content = document_input
    else:
        # Otherwise, treat the input as the document content
        document_content = document_input
        print(f"\nAssistant: Document content received. Content preview:\n\n{document_content[:200]}...\n")
    
    # Get target language
    print("Assistant: Please specify the target language for translation.")
    target_language = input("\nYou: ").strip()
    
    # Check for exit command
    if target_language.lower() in ['exit', 'quit', 'q']:
        print("Exiting translation process.")
        return
    
    print(f"\nAssistant: Target language set to: {target_language}. Starting translation process...\n")
    
    # Update the state with document content and target language
    state["document_content"] = document_content
    state["target_language"] = target_language
    
    # Add the initial user request to the messages
    state["messages"].append(HumanMessage(content=f"Please translate this document to {target_language} and ensure it has good readability."))
    
    # Run the workflow
    print("Assistant: Running the translation workflow...\n")
    
    # Stream the results for visibility
    for step in translation_graph.stream(state):
        # If there's a new message, print it
        if "messages" in step and step["messages"] and isinstance(step["messages"][-1], AIMessage):
            print(f"Assistant: {step['messages'][-1].content}\n")
    
    # Get the final state
    final_state = translation_graph.invoke(state)
    
    # Check if we have a translation
    if final_state.get("translated_content"):
        # Ask if the user wants to save the translation
        save_option = input("\nDo you want to save the translation? (y/n): ").strip().lower()
        if save_option == 'y':
            output_file = input("Enter output filename: ").strip()
            save_translation({
                "target_language": final_state["target_language"],
                "translated_content": final_state["translated_content"],
                "readability_score": final_state["readability_score"],
                "revision_needed": final_state["revision_needed"],
            }, output_file)
        
        print("\nTranslation process completed!")
    else:
        print("\nTranslation process failed. Please try again.")

def run_batch_translation(input_file: str, target_language: str, output_file: Optional[str] = None):
    """Run the translation workflow in batch mode."""
    # Create the workflow graph
    translation_graph = create_translation_graph()
    
    # Set default output file if not provided
    if not output_file:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_{target_language}.txt"
    
    print(f"Translating '{input_file}' to {target_language}...")
    
    # Load document content
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            document_content = file.read()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        return
    
    # Initial state
    state = {
        "messages": [HumanMessage(content=f"Please translate this document to {target_language} and ensure it has good readability.")],
        "document_content": document_content,
        "target_language": target_language
    }
    
    # Run the workflow
    print("Running the translation workflow...")
    
    # Stream the results for visibility
    for step in translation_graph.stream(state):
        # If there's a new message, print it
        if "messages" in step and step["messages"] and isinstance(step["messages"][-1], AIMessage):
            # Split the content and get the first line
            content_lines = step['messages'][-1].content.split('\n')
            first_line = content_lines[0] if content_lines else ""
            print(f"- {first_line}")
    
    # Get the final state
    final_state = translation_graph.invoke(state)
    
    # Check if we have a translation
    if final_state.get("translated_content"):
        # Save the translation
        save_translation({
            "target_language": final_state["target_language"],
            "translated_content": final_state["translated_content"],
            "readability_score": final_state["readability_score"],
            "revision_needed": final_state["revision_needed"],
        }, output_file)
        
        print(f"Readability score: {final_state['readability_score']}/10")
        if final_state.get("revision_needed"):
            print("Note: The translation was revised to improve readability.")
    else:
        print("Translation process failed. Please try again.")

def main():
    """Main function to parse arguments and run the appropriate mode."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Agent Document Translator with Readability Testing")
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
