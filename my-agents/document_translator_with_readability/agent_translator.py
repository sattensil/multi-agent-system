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
import datetime
import io
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
- If the document is already in the target language, skip translation and go directly to readability testing
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
You may receive a document that is already in the target language, in which case you should return the original content.
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
    
    # Check if we just completed a successful revision
    last_message = state["messages"][-1] if state["messages"] else None
    readability_score = state.get("readability_score")
    previous_score = state.get("previous_readability_score")
    
    # If we have a good readability score after revision, go straight to FINISH
    if (last_message and "revised translation" in last_message.content.lower() and 
            readability_score is not None and readability_score >= 7.0 and
            previous_score is not None and readability_score > previous_score):
        print("\n" + "=" * 80)
        print("🎉 WORKFLOW COMPLETE: Revision successful with good readability score")
        print(f"📊 Final readability score: {readability_score}/10 (improved from {previous_score})")
        print("=" * 80)
        state["messages"].append(AIMessage(content="Translation process completed successfully after revision."))
        return Command(goto=END, update={"next": "FINISH"})
    
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
    
    print("\n" + "=" * 80)
    print("🧠 SUPERVISOR AGENT: Deciding next step...")
    print("-" * 80)
    
    # Check if document is already in the target language and we haven't processed it yet
    document_content = state.get("document_content")
    target_language = state.get("target_language")
    translated_content = state.get("translated_content")
    
    if document_content and target_language and not translated_content:
        # Simple language detection - this is a basic check
        # For a real application, use a language detection library
        system_prompt = f"""
        You are a language detection specialist. Determine if the following text is in {target_language}.
        Respond with only 'yes' or 'no'.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=document_content[:500])  # Use first 500 chars for detection
        ]
        
        print(f"🔍 Checking if document is already in {target_language}...")
        response = llm.invoke(messages)
        is_target_language = 'yes' in response.content.lower()
        
        if is_target_language:
            print(f"✅ Document is already in {target_language}, skipping translation")
            # Update the state with the original document as the translated content
            state["translated_content"] = document_content
            state["messages"].append(AIMessage(
                content=f"The document is already in {target_language}. Skipping translation and proceeding to readability assessment."
            ))
            # Return a command to go to readability testing with the updated state
            return Command(goto="readability_tester", update={
                "next": "readability_tester",
                "translated_content": document_content  # Explicitly include in update
            })
    
    response = llm.with_structured_output(Router).invoke(state["messages"])
    goto = response["next"]
    reason = response["reason"]
    
    print(f"✅ DECISION: Call the {goto} agent")
    print(f"📝 REASON: {reason}")
    print("=" * 80)
    
    # Add the supervisor's decision to the messages
    state["messages"].append(AIMessage(content=f"I've decided to call the {goto} agent. Reason: {reason}"))
    
    if goto == "FINISH":
        print("\n" + "=" * 80)
        print("🎉 WORKFLOW COMPLETE: Translation process finished successfully")
        print("=" * 80)
        state["messages"].append(AIMessage(content="Translation process completed successfully."))
        return Command(goto=END, update={"next": "FINISH"})
    
    return Command(goto=goto, update={"next": goto})

def translator_node(state: State) -> State:
    """Translator agent that translates the document."""
    document_content = state.get("document_content")
    target_language = state.get("target_language")
    
    print("\n" + "=" * 80)
    print(f"🔤 TRANSLATOR AGENT: Translating document to {target_language}...")
    print("-" * 80)
    
    if not document_content or not target_language:
        error_msg = "Error: Missing document content or target language."
        print(f"❌ ERROR: {error_msg}")
        state["messages"].append(AIMessage(content=error_msg))
        return state
    
    system_prompt = f"""
    {TRANSLATOR_PROMPT}
    
    Translate the following document from English to {target_language}.
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=document_content)
    ]
    
    print(f"📝 Processing document ({len(document_content)} characters)...")
    response = llm.invoke(messages)
    translated_content = response.content
    
    state["translated_content"] = translated_content
    preview = translated_content[:200] + "..." if len(translated_content) > 200 else translated_content
    print(f"✅ TRANSLATION COMPLETE: Document translated to {target_language}")
    print(f"📄 PREVIEW:\n{preview}")
    print("=" * 80)
    
    state["messages"].append(AIMessage(content=f"I've translated the document to {target_language}. Here's a preview:\n\n{translated_content[:200]}..."))
    
    return state

def readability_tester_node(state: State) -> State:
    """Readability tester agent that assesses the readability of the translation."""
    translated_content = state.get("translated_content")
    target_language = state.get("target_language")
    previous_score = state.get("previous_readability_score")
    
    print("\n" + "=" * 80)
    print(f"📊 READABILITY TESTER AGENT: Assessing {target_language} translation...")
    print("-" * 80)
    
    if not translated_content or not target_language:
        error_msg = "Error: Missing translated content or target language."
        print(f"❌ ERROR: {error_msg}")
        state["messages"].append(AIMessage(content=error_msg))
        return state
    
    # Check if we're coming from a revision
    coming_from_revision = state.get("next") == "readability_tester" and previous_score is None and state.get("readability_score") is None
    
    system_prompt = f"""
    {READABILITY_TESTER_PROMPT}
    
    Assess the readability of the following {target_language} text.
    IMPORTANT: Your response MUST include a numerical score in the format 'X/10' or 'Score: X' where X is a number between 1 and 10.
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=translated_content)
    ]
    
    print("📝 Analyzing readability...")
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
            # Raise an error instead of using a default score
            error_msg = "Error: Could not extract a readability score from the assessment."
            print(f"❌ {error_msg}")
            print(f"Raw feedback: {feedback[:200]}...")
            raise ValueError(error_msg)
    
    # Validate the score is within the expected range
    if readability_score < 1 or readability_score > 10:
        error_msg = f"Error: Readability score {readability_score} is outside the valid range (1-10)."
        print(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    # Store the previous score before updating if we're coming from a revision
    if coming_from_revision and state.get("readability_score") is not None:
        state["previous_readability_score"] = state["readability_score"]
    
    state["readability_score"] = readability_score
    state["revision_needed"] = readability_score < 7.0
    
    print(f"✅ ASSESSMENT COMPLETE: Readability score = {readability_score}/10")
    print(f"📝 FEEDBACK:\n{feedback[:300]}{'...' if len(feedback) > 300 else ''}")
    
    # Add information about improvement if we're coming from a revision
    if coming_from_revision and state.get("previous_readability_score") is not None:
        previous_score = state["previous_readability_score"]
        improvement = readability_score - previous_score
        print(f"📈 IMPROVEMENT: Score increased by {improvement:.1f} points (from {previous_score:.1f} to {readability_score:.1f})")
    
    if state["revision_needed"]:
        print(f"⚠️ REVISION NEEDED: Score below threshold of 7.0")
    else:
        print(f"✅ NO REVISION NEEDED: Score meets or exceeds threshold of 7.0")
    print("=" * 80)
    
    # Create a more detailed message if we're coming from a revision
    if coming_from_revision:
        message_content = f"I've assessed the readability of the revised translation. Score: {readability_score}/10\n\nFeedback: {feedback}"
        if state.get("previous_readability_score") is not None:
            previous_score = state["previous_readability_score"]
            improvement = readability_score - previous_score
            message_content += f"\n\nThe revision has improved the readability score by {improvement:.1f} points (from {previous_score:.1f} to {readability_score:.1f})."
    else:
        message_content = f"I've assessed the readability of the translation. Score: {readability_score}/10\n\nFeedback: {feedback}"
    
    state["messages"].append(AIMessage(content=message_content))
    
    return state

def reviser_node(state: State) -> Command[Literal["readability_tester"]]:
    """Reviser agent that improves the translation based on readability feedback."""
    translated_content = state.get("translated_content")
    target_language = state.get("target_language")
    readability_score = state.get("readability_score")
    
    print("\n" + "=" * 80)
    print(f"✏️ REVISER AGENT: Improving {target_language} translation...")
    print("-" * 80)
    
    if not translated_content or not target_language or readability_score is None:
        error_msg = "Error: Missing translated content, target language, or readability score."
        print(f"❌ ERROR: {error_msg}")
        state["messages"].append(AIMessage(content=error_msg))
        # Return to supervisor to handle the error
        return Command(goto="supervisor", update={"next": "supervisor"})
    
    # Get the last message which should contain the readability feedback
    feedback = ""
    for message in reversed(state["messages"]):
        if "I've assessed the readability" in message.content:
            feedback = message.content
            break
    
    print(f"📝 Current readability score: {readability_score}/10")
    print("📝 Revising translation to improve readability...")
    
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
    
    # Update the state with the revised content
    state["translated_content"] = revised_content
    # Store the current score as previous_readability_score before resetting
    state["previous_readability_score"] = readability_score
    # Reset the readability score to force reassessment
    state["readability_score"] = None
    state["revision_needed"] = None
    
    preview = revised_content[:200] + "..." if len(revised_content) > 200 else revised_content
    print(f"✅ REVISION COMPLETE: Translation revised for better readability")
    print(f"📄 PREVIEW:\n{preview}")
    print("🔄 Sending revised content for readability assessment")
    print("=" * 80)
    
    state["messages"].append(AIMessage(content=f"I've revised the translation to improve readability. Here's a preview:\n\n{revised_content[:200]}...\n\nNow we need to reassess the readability of the revised content."))
    
    # Directly go to readability testing with the revised content
    return Command(goto="readability_tester", update={
        "next": "readability_tester",
        "translated_content": revised_content,
        "previous_readability_score": readability_score,  # Store the previous score
        "readability_score": None,  # Reset score to force reassessment
        "revision_needed": None
    })

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
    workflow.add_edge("reviser", "readability_tester")  # Reviser goes directly to readability testing
    
    # Compile the graph
    return workflow.compile()

def save_translation(translation_data: Dict, output_file: str) -> None:
    """Save the translation to a file."""
    try:
        # Ensure we have the necessary keys with defaults if missing
        translated_content = translation_data.get("translated_content", "")
        target_language = translation_data.get("target_language", "Unknown")
        readability_score = translation_data.get("readability_score", 0)
        revisions_made = translation_data.get("revisions_made", False)
        
        # Write the translation content to the output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(translated_content)
        
        # Save metadata to a JSON file
        import json
        metadata_file = f"{os.path.splitext(output_file)[0]}_metadata.json"
        metadata = {
            "target_language": target_language,
            "readability_score": readability_score,
            "revisions_made": revisions_made,
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Translation saved to: {output_file}")
        print(f"Metadata saved to: {metadata_file}")
    except Exception as e:
        print(f"\nWarning: Could not save translation completely: {str(e)}")

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
    
    print("\n" + "=" * 80)
    print(f"🚀 STARTING TRANSLATION WORKFLOW")
    print(f"📄 Input file: {input_file}")
    print(f"🌐 Target language: {target_language}")
    if output_file:
        print(f"📝 Output file: {output_file}")
    print("=" * 80)
    
    # Set default output file if not provided
    if not output_file:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_{target_language}.txt"
    
    # Load document content
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            document_content = file.read()
            print(f"✅ Document loaded: {len(document_content)} characters")
    except FileNotFoundError:
        print(f"❌ ERROR: File '{input_file}' not found.")
        return
    
    # Initial state
    state = {
        "messages": [HumanMessage(content=f"Please translate this document to {target_language} and ensure it has good readability.")],
        "document_content": document_content,
        "target_language": target_language
    }
    
    # Set up logging to capture terminal output
    log_date = datetime.datetime.now().strftime("%Y_%m_%d")
    log_filename = f"{os.path.splitext(os.path.basename(input_file))[0]}_{target_language}_{log_date}.txt"
    log_path = os.path.join(os.path.dirname(os.path.abspath(input_file)), log_filename)
    
    # Create a custom stdout that writes to both console and log
    class TeeOutput:
        def __init__(self, file):
            self.file = file
            self.terminal = sys.stdout
            self.log = []
        
        def write(self, message):
            self.terminal.write(message)
            self.log.append(message)
        
        def flush(self):
            self.terminal.flush()
    
    # Save the original stdout
    original_stdout = sys.stdout
    # Create our custom output handler
    tee_output = TeeOutput(log_path)
    
    try:
        # Redirect stdout to our tee output
        sys.stdout = tee_output
        
        print(f"\nLog file will be saved to: {log_path}\n")
        
        # Run the workflow - we don't need to print anything here as the agent nodes will handle output
        # Set a recursion limit to prevent infinite loops
        result = translation_graph.invoke(state, config={"recursion_limit": 10})
        
        # Check if we have a translation
        if result.get("translated_content"):
            # Determine if revisions were made
            revisions_made = False
            if result.get("previous_readability_score") is not None:
                revisions_made = True
            
            # Prepare the translation data with safe access to dictionary keys
            translation_data = {
                "target_language": result.get("target_language", target_language),
                "translated_content": result.get("translated_content", ""),
                "readability_score": result.get("readability_score", 0),
                "revisions_made": revisions_made
            }
            
            # Save the translation
            save_translation(translation_data, output_file)
            
            print("\n" + "=" * 80)
            print("📊 FINAL RESULTS:")
            print(f"✅ Translation saved to: {output_file}")
            try:
                if "readability_score" in result:
                    print(f"📊 Readability score: {result['readability_score']}/10")
                    if result.get("previous_readability_score") is not None:
                        print(f"🔄 Note: The translation was revised to improve readability (from {result.get('previous_readability_score', 0)}/10 to {result['readability_score']}/10).")
                else:
                    print("⚠️ Note: Readability assessment was not completed.")
            except Exception as e:
                print(f"⚠️ Note: Could not display complete readability information: {str(e)}")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ TRANSLATION FAILED: No translated content available.")
            print("=" * 80)
    except ValueError as e:
        print("\n" + "=" * 80)
        print(f"❌ TRANSLATION ERROR: {str(e)}")
        print("=" * 80)
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ UNEXPECTED ERROR: {str(e)}")
        print("=" * 80)
    finally:
        # Restore the original stdout
        sys.stdout = original_stdout
        
        # Save the captured output to the log file
        with open(log_path, 'w', encoding='utf-8') as log_file:
            log_file.write(''.join(tee_output.log))
        
        print(f"\nLog saved to: {log_path}")

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
