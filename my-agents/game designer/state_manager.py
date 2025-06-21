import asyncio
import json
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

class GameDesignState(Enum):
    """Enumeration of game design workflow states."""
    INITIAL = "initial"                    # Starting state
    PROJECT_MANAGER = "project_manager"    # Project Manager decision point
    THEME_RESEARCH = "theme_research"      # Domain Scholar researches theme
    MECHANIC_DESIGN = "mechanic_design"    # Gameplay Expert designs mechanics
    PLAYTEST = "playtest"                  # Test players evaluate the game
    FACT_CHECK = "fact_check"              # Fact Checker validates content
    VISUAL_DESIGN = "visual_design"        # Art Director creates visual specs
    FINAL_REVIEW = "final_review"          # Final review of all materials
    COMPLETE = "complete"                  # Design process complete

class TransitionAction(Enum):
    """Enumeration of actions the Project Manager can take."""
    THEME_RESEARCH = "THEME_RESEARCH"      # Conduct theme research with Domain Scholar
    MECHANIC_DESIGN = "MECHANIC_DESIGN"    # Design mechanics with Gameplay Expert
    PLAYTEST = "PLAYTEST"                  # Playtest with test players
    FACT_CHECK = "FACT_CHECK"              # Fact check with Fact Checker
    VISUAL_DESIGN = "VISUAL_DESIGN"        # Create visual design with Art Director
    REVISE_THEME = "REVISE_THEME"          # Revise the theme research
    REVISE_MECHANICS = "REVISE_MECHANICS"  # Revise the game mechanics
    FINAL_REVIEW = "FINAL_REVIEW"          # Conduct a final review
    COMPLETE = "COMPLETE"                  # Complete the design process

class SupervisorManager:
    """Manager for the Project Manager supervisor state transitions."""
    
    def __init__(self):
        """Initialize the supervisor manager."""
        self.revision_history = []
        self.project_manager = None
    
    async def determine_next_state(self, 
                              current_state: GameDesignState, 
                              artifacts: Dict[str, Any],
                              iteration_counts: Dict[GameDesignState, int]) -> Tuple[GameDesignState, str]:
        """
        Have the Project Manager determine the next state in the workflow.
        
        Args:
            current_state: The current state in the workflow
            artifacts: Dictionary of design artifacts from each stage
            iteration_counts: Count of iterations for each state
        
        Returns:
            Tuple of (next_state, reason)
        """
        # Build the prompt for the Project Manager to make a decision
        prompt = self._build_supervisor_prompt(current_state, artifacts, iteration_counts)
        
        print("\n[API CALL] Running Project Manager agent to determine next state...")
        # Create a Runner instance and call run with the agent and prompt
        runner = Runner()
        result = await runner.run(self.project_manager, prompt)
        
        # Extract text content from result (similar to what we did in manager.py)
        result_text = ""
        clean_text = ""
        
        # First get the raw result
        if hasattr(result, 'content'):
            result_text = result.content
        elif hasattr(result, 'text'):
            result_text = result.text
        elif hasattr(result, 'new_items') and result.new_items:
            # Try to get text from new_items if it exists
            result_text = result.new_items[0].text if hasattr(result.new_items[0], 'text') else str(result.new_items[0])
        else:
            # Fallback to string representation
            result_text = str(result)
        
        # Try to extract the clean text content efficiently
        clean_text = ""
        
        # If it's a direct string, use it
        if isinstance(result_text, str):
            clean_text = result_text
        # Otherwise try to extract text from MessageOutputItem structure
        else:
            try:
                # First try the raw_item.content path (most common)
                if hasattr(result_text, 'raw_item') and hasattr(result_text.raw_item, 'content'):
                    content_items = result_text.raw_item.content
                    if isinstance(content_items, list) and len(content_items) > 0:
                        for item in content_items:
                            if hasattr(item, 'text'):
                                clean_text = item.text
                                break
                
                # If we still don't have text, look for other common patterns
                if not clean_text and hasattr(result_text, 'text'):
                    clean_text = result_text.text
                
                # Last resort - try to extract from string representation
                if not clean_text:
                    text_str = str(result_text)
                    # Look for JSON content in the text
                    import re
                    json_match = re.search(r'{[^}]+}', text_str, re.DOTALL)
                    if json_match:
                        clean_text = json_match.group(0)
                    else:
                        # If not JSON, look for text= attribute
                        if "text=\"" in text_str:
                            parts = text_str.split("text=\"")
                            if len(parts) > 1:
                                text_part = parts[1]
                                end_quote_pos = text_part.rfind('"')
                                if end_quote_pos != -1:
                                    clean_text = text_part[:end_quote_pos]
                        else:
                            clean_text = "Unable to extract clean text from response"
            except Exception as e:
                clean_text = f"Error extracting text: {e}"
        
        # Only print the decision content, not the full structure
        print("\n[STATE REASONING] Project Manager's decision:")
        try:
            # Try to extract just the decision and reason
            import re
            import json
            
            decision_str = ""
            reason_str = ""
            
            # Look for decision and reason in JSON format
            decision_match = re.search(r'"decision"\s*:\s*"([^"]+)"', clean_text)
            reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', clean_text)
            
            if decision_match:
                decision_str = decision_match.group(1)
                print(f"Decision: {decision_str}")
            
            if reason_match:
                reason_str = reason_match.group(1)
                print(f"Reason: {reason_str}")
            
            if not decision_str and not reason_str:
                # Just print the cleaned text if we couldn't extract specific fields
                print(clean_text)
        except Exception:
            # If extraction fails, print the clean text
            print(clean_text)
        
        # Parse the decision using the extracted text
        next_state, reason = self._parse_decision(result_text, current_state)
        
        # Print the final decision and reasoning
        print(f"\n[STATE TRANSITION] Decision: {current_state.value} → {next_state.value}")
        print(f"[STATE TRANSITION] Reasoning: {reason}\n")
        
        # Record the transition in the revision history
        self.revision_history.append({
            "from_state": current_state.value,
            "to_state": next_state.value,
            "reason": reason,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        return next_state, reason
    
    def _build_supervisor_prompt(self, 
                           current_state: GameDesignState, 
                           artifacts: Dict[str, Any],
                           iteration_counts: Dict[GameDesignState, int]) -> str:
        """Build the prompt for the Project Manager to make a decision."""

        # Start with the basic prompt structure emphasizing Project Manager's central role
        prompt = f"""As the Project Manager, you are the central coordinator for this board game design project. 
        You make decisions about which specialist should work on the game next based on the current state and progress.

        CURRENT STATE: {current_state.value}

        ITERATION COUNTS:
        - Mechanic Design: {iteration_counts.get(GameDesignState.MECHANIC_DESIGN, 0)}/3
        - Playtesting: {iteration_counts.get(GameDesignState.PLAYTEST, 0)}/3
        - Fact Checking: {iteration_counts.get(GameDesignState.FACT_CHECK, 0)}/2

        DESIGN WORKFLOW PRINCIPLES:
        - Theme must be properly researched and fact-checked before finalizing mechanics
        - Playtests must be evaluated and feedback incorporated into design
        - Visual design should only start after gameplay is solid and fact-checked
        - All components should be reviewed before completion

        AVAILABLE ACTIONS:
        - THEME_RESEARCH: Send to Domain Scholar for theme research
        - MECHANIC_DESIGN: Send to Gameplay Expert for mechanics design
        - PLAYTEST: Send to Test Players for playtesting
        - FACT_CHECK: Send to Fact Checker to verify accuracy
        - VISUAL_DESIGN: Send to Art Director for visual specifications
        - REVISE_THEME: Return to Domain Scholar for theme revision
        - REVISE_MECHANICS: Return to Gameplay Expert for mechanics revision
        - FINAL_REVIEW: Conduct final review of all materials
        - COMPLETE: Finalize the design process

        """

        # Add relevant information based on the current state
        if current_state == GameDesignState.INITIAL:
            prompt += """
            DECISION NEEDED:
            We're at the beginning of the project. The next logical step is to conduct theme research.
            Should we proceed to theme research? (This is almost always yes unless there's a problem with the initial concept)
            """

        elif current_state == GameDesignState.THEME_RESEARCH:
            theme_research = artifacts.get("theme_research", {}).get("content", "")
            prompt += f"""
            THEME RESEARCH COMPLETED:
            {theme_research[:500]}... [truncated]

            DECISION NEEDED:
            Now that we have theme research, should we proceed to game mechanics design?
            """

        elif current_state == GameDesignState.MECHANIC_DESIGN:
            mechanics = artifacts.get("mechanics_design", {}).get("content", "")
            prompt += f"""
            GAME MECHANICS COMPLETED (Iteration {iteration_counts.get(GameDesignState.MECHANIC_DESIGN, 0) + 1}/3):
            {mechanics[:500]}... [truncated]

            DECISION NEEDED:
            Now that we have game mechanics, should we proceed to playtesting or revise the mechanics further?
            - PROCEED: Move to playtesting to evaluate the current mechanics
            - REVISE_MECHANICS: The mechanics need more work before playtesting
            """

        elif current_state == GameDesignState.PLAYTEST:
            playtest_results = artifacts.get("playtest_results", {}).get("content", "")
            prompt += f"""
            PLAYTEST RESULTS (Iteration {iteration_counts.get(GameDesignState.PLAYTEST, 0) + 1}/3):
            {playtest_results[:500]}... [truncated]

            DECISION NEEDED:
            Based on the playtest results, should we:
            - PROCEED: Move to fact checking as the mechanics are solid
            - REVISE_MECHANICS: The mechanics need refinement based on playtest feedback
            """

        elif current_state == GameDesignState.FACT_CHECK:
            fact_check = artifacts.get("fact_check_results", {}).get("content", "")
            prompt += f"""
            FACT CHECK RESULTS (Iteration {iteration_counts.get(GameDesignState.FACT_CHECK, 0) + 1}/2):
            {fact_check[:500]}... [truncated]

            DECISION NEEDED:
            Based on the fact checking, should we:
            - PROCEED: Move to visual design as the factual aspects are correct
            - REVISE_THEME: The theme research needs refinement based on fact checking
            - REVISE_MECHANICS: The mechanics need refinement based on fact checking
            """

        elif current_state == GameDesignState.VISUAL_DESIGN:
            visual_design = artifacts.get("visual_design", {}).get("content", "")
            prompt += f"""
            VISUAL DESIGN COMPLETED:
            {visual_design[:500]}... [truncated]

            DECISION NEEDED:
            Now that we have visual design, should we:
            - PROCEED: Move to final review as the design is complete
            - REVISE_MECHANICS: The mechanics need adjustment based on visual design considerations
            """

        elif current_state == GameDesignState.FINAL_REVIEW:
            prompt += """
            FINAL REVIEW COMPLETED:

            DECISION NEEDED:
            Is the game design complete and ready for production?
            - COMPLETE: The game design is finalized and ready for production
            - REVISE_MECHANICS: Final adjustments needed to mechanics
            - REVISE_THEME: Final adjustments needed to theme
            """

        # Add standard format instructions
        prompt += """RESPONSE FORMAT:
Respond with a JSON object containing:
1. "decision": One of [THEME_RESEARCH, MECHANIC_DESIGN, PLAYTEST, FACT_CHECK, VISUAL_DESIGN, REVISE_THEME, REVISE_MECHANICS, FINAL_REVIEW, COMPLETE]
2. "reason": A brief explanation of your decision (1-2 sentences max)

Example:
{
  "decision": "THEME_RESEARCH",
  "reason": "We need to establish a solid thematic foundation before developing mechanics."
}

Think carefully about your decision based on the current state and principles. Remember to send the design to the Art Director for visual specifications once the gameplay is solid and fact-checked.
"""

        return prompt

    def _parse_decision(self, decision_text: str, current_state: GameDesignState) -> Tuple[GameDesignState, str]:
        """Parse the Project Manager's decision text to determine the next state."""
        # Default to starting with theme research if no other decision is detected
        decision = TransitionAction.THEME_RESEARCH
        reason = "Moving to theme research by default."
        
        # Try to extract the decision from the text using a direct approach
        try:
            import re
            import json
            
            # Check for JSON in code blocks first
            json_match = re.search(r'```(?:json)?\s*({[^}]+})\s*```', decision_text, re.DOTALL)
            if json_match:
                raw_json = json_match.group(1)
            else:
                # Find any JSON-like structure in the text
                json_match = re.search(r'{[^}]+}', decision_text, re.DOTALL)
                if json_match:
                    raw_json = json_match.group(0)
                else:
                    raise ValueError("No JSON structure found")
            
            # Clean up the JSON by properly handling property names and values
            # Convert to a single line first to make regex easier
            cleaned_json = raw_json.replace('\n', ' ').replace('\r', '')
            
            # Make sure property names are quoted
            cleaned_json = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', cleaned_json)
            
            # Handle the JSON parsing directly without using json.loads
            # Extract decision
            decision_match = re.search(r'"decision"\s*:\s*"([^"]+)"', cleaned_json)
            if decision_match:
                decision_value = decision_match.group(1).upper()
                # Map the decision text to a TransitionAction
                for action in TransitionAction:
                    if action.value.upper() == decision_value:
                        decision = action
                        break
            
            # Extract reason
            reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', cleaned_json)
            if reason_match:
                reason = reason_match.group(1)
            
        except Exception as e:
            print(f"Error parsing decision: {e}")
            # Continue with default decision
        
        # Fallback to simple text parsing if JSON parsing failed
        if decision == TransitionAction.THEME_RESEARCH and "REVISE_MECHANICS" in decision_text.upper():
            decision = TransitionAction.REVISE_MECHANICS
        elif decision == TransitionAction.THEME_RESEARCH and "REVISE_THEME" in decision_text.upper():
            decision = TransitionAction.REVISE_THEME
        elif decision == TransitionAction.THEME_RESEARCH and "FINAL_REVIEW" in decision_text.upper():
            decision = TransitionAction.FINAL_REVIEW
        elif decision == TransitionAction.THEME_RESEARCH and "COMPLETE" in decision_text.upper():
            decision = TransitionAction.COMPLETE
        
        # Special case: For testing purposes in test_run.py, if we're in the INITIAL state,
        # make sure we follow the proper workflow sequence instead of jumping to COMPLETE
        if current_state == GameDesignState.INITIAL:
            # Always go to THEME_RESEARCH from INITIAL
            next_state = GameDesignState.THEME_RESEARCH
        else:
            # Determine the next state based on the current state and decision
            next_state = self._get_next_state(current_state, decision)
        
        return next_state, reason

    def _get_next_state(self, current_state: GameDesignState, decision: TransitionAction) -> GameDesignState:
        """Get the next state based on the current state and transition action."""
        # Initial state always goes to Project Manager first
        if current_state == GameDesignState.INITIAL:
            return GameDesignState.PROJECT_MANAGER
            
        # Any task state (besides PROJECT_MANAGER and COMPLETE) returns to Project Manager for evaluation
        if current_state not in [GameDesignState.PROJECT_MANAGER, GameDesignState.COMPLETE]:
            return GameDesignState.PROJECT_MANAGER
            
        # Project Manager can direct to any state based on decision
        if current_state == GameDesignState.PROJECT_MANAGER:
            # Map TransitionAction to corresponding GameDesignState
            action_to_state = {
                TransitionAction.THEME_RESEARCH: GameDesignState.THEME_RESEARCH,
                TransitionAction.MECHANIC_DESIGN: GameDesignState.MECHANIC_DESIGN,
                TransitionAction.PLAYTEST: GameDesignState.PLAYTEST,
                TransitionAction.FACT_CHECK: GameDesignState.FACT_CHECK,
                TransitionAction.VISUAL_DESIGN: GameDesignState.VISUAL_DESIGN,
                TransitionAction.REVISE_THEME: GameDesignState.THEME_RESEARCH,
                TransitionAction.REVISE_MECHANICS: GameDesignState.MECHANIC_DESIGN,
                TransitionAction.FINAL_REVIEW: GameDesignState.FINAL_REVIEW,
                TransitionAction.COMPLETE: GameDesignState.COMPLETE
            }
            
            # Return the corresponding state or stay in PROJECT_MANAGER if decision is invalid
            return action_to_state.get(decision, GameDesignState.PROJECT_MANAGER)
        
        # Default: stay in current state
        return current_state

    def format_revision_history(self) -> str:
        """Format the revision history as a markdown document."""
        if not self.revision_history:
            return "No revisions recorded."
        
        history = "# Design Revision History\n\n"
        
        for i, revision in enumerate(self.revision_history):
            history += f"## Revision {i+1}\n"
            history += f"- From: {revision['from_state']}\n"
            history += f"- To: {revision['to_state']}\n"
            history += f"- Reason: {revision['reason']}\n\n"
        
        return history

# Import at the end to avoid circular imports
from agents import Runner
