import asyncio
import os
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv
from weasyprint import HTML
import markdown

from agents import Agent, Runner
from agents.result import RunResult
# Change relative imports to absolute imports
from agent_factories import (
    create_project_manager_agent,
    create_gameplay_expert_agent,
    create_domain_scholar_agent,
    create_fact_checker_agent,
    create_test_player_agent,
    create_art_director_agent
)
from state_manager import SupervisorManager, GameDesignState, TransitionAction

# Load environment variables
load_dotenv()

# Helper function for running agents consistently
async def run_agent_with_prompt(agent, prompt, agent_name=None):
    """Run an agent with the given prompt and return the result."""
    if agent_name:
        print(f"\n[API CALL] Running {agent_name} agent...")
    
    # Create a Runner instance without passing the agent (since Runner() takes no arguments)
    runner = Runner()
    
    # The Runner.run method expects the agent and the prompt text directly, not wrapped in a dict
    return await runner.run(agent, prompt)

class BoardGameDesignManager:
    """Manager for the board game design workflow using multiple specialized agents."""

    def __init__(self):
        """Initialize the board game design manager with specialized agents."""
        # Initialize agents
        self.project_manager = create_project_manager_agent()  # Add this line to initialize project_manager
        self.gameplay_expert = create_gameplay_expert_agent()
        self.domain_scholar = create_domain_scholar_agent()
        self.fact_checker = create_fact_checker_agent()
        self.art_director = create_art_director_agent()
        
        print("[STATUS] Initialized all agent modules successfully.")
        
        # Create the supervisor manager (Project Manager as supervisor)
        self.supervisor = SupervisorManager()
        # Set the project_manager in the supervisor
        self.supervisor.project_manager = self.project_manager
        
        # Test player agents will be created based on the game requirements
        self.test_players = []
        
        # Create output directory if it doesn't exist
        self.output_dir = Path(__file__).parent / "generated_games"
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize state machine variables
        self.current_state = GameDesignState.INITIAL
        self.iteration_count = {
            GameDesignState.MECHANIC_DESIGN: 0,
            GameDesignState.PLAYTEST: 0,
            GameDesignState.FACT_CHECK: 0
        }
        self.max_iterations = {
            GameDesignState.MECHANIC_DESIGN: 3,  # Max 3 mechanic revision iterations
            GameDesignState.PLAYTEST: 3,         # Max 3 playtest iterations
            GameDesignState.FACT_CHECK: 2        # Max 2 fact checking iterations
        }
        
        # Store design artifacts for each stage
        self.design_artifacts = {
            "project_plan": {},
            "theme_research": {},
            "mechanics_design": {},
            "playtest_results": {},
            "fact_check_results": {},
            "visual_design": {},
            "final_design": {}
        }
        
        # Store revision history and feedback
        self.revision_history = []
        
        # Create a log directory for workflow tracking
        self.log_dir = self.output_dir / "_workflow_logs"
        self.log_dir.mkdir(exist_ok=True)

    async def run(self, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the board game design workflow using a state machine approach with the Project Manager as supervisor.
        
        Args:
            user_preferences: Dictionary containing user preferences and game requirements
            
        Returns:
            Dictionary containing the final game design with all components
        """
        print("✅ Starting board game design process...")
        
        # Generate game name if not provided
        if not user_preferences.get("game_name"):
            user_preferences["game_name"] = await self._generate_game_name(
                user_preferences.get("theme", ""),
                user_preferences.get("design_focus", "")
            )
            print(f"Generated game name: {user_preferences['game_name']}")
        
        # Create specific game output directory
        game_dir = self.output_dir / user_preferences["game_name"].replace(" ", "_")
        game_dir.mkdir(exist_ok=True)
        
        # Store user preferences
        self.user_preferences = user_preferences
        self.game_dir = game_dir
        
        # Reset the state machine
        self.current_state = GameDesignState.INITIAL
        
        # Create a workflow log file
        workflow_log = game_dir / "workflow_log.md"
        with open(workflow_log, "w", encoding="utf-8") as f:
            f.write(f"# {user_preferences['game_name']} Design Workflow Log\n\n")
            f.write(f"Started on: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write("## Workflow States\n\n")
        
        # Run the state machine until we reach the COMPLETE state
        while self.current_state != GameDesignState.COMPLETE:
            # Log the current state
            print(f"\n=== CURRENT STATE: {self.current_state.value.upper()} ===\n")
            self._append_to_log(workflow_log, f"### State: {self.current_state.value}\n\n")
            
            # Process the current state
            await self._process_current_state()
            
            # Let the supervisor (Project Manager) decide the next state
            next_state, reason = await self.supervisor.determine_next_state(
                self.current_state,
                self.design_artifacts,
                self.iteration_count
            )
            
            # Log the transition
            transition_text = f"**Transition:** {self.current_state.value} → {next_state.value}\n\n"
            transition_text += f"**Reason:** {reason}\n\n"
            transition_text += f"**Iteration counts:**\n"
            for state, count in self.iteration_count.items():
                transition_text += f"- {state.value}: {count}\n"
            self._append_to_log(workflow_log, transition_text)
            
            # Update iteration count if we're revisiting a state
            if next_state in self.iteration_count and self.current_state != next_state:
                self.iteration_count[next_state] += 1
            
            # Check if we've reached the maximum iterations for a state
            if next_state in self.max_iterations and self.iteration_count[next_state] > self.max_iterations[next_state]:
                print(f"Maximum iterations ({self.max_iterations[next_state]}) reached for {next_state.value}.")
                print(f"Moving to {GameDesignState.ART_DIRECTION.value} despite potential issues.")
                self._append_to_log(workflow_log, f"⚠️ **Maximum iterations reached for {next_state.value}. Proceeding to art direction.**\n\n")
                next_state = GameDesignState.ART_DIRECTION
            
            # Update the current state
            self.current_state = next_state
        
        # We've reached the COMPLETE state, finalize everything
        print("\n=== PHASE 5: FINAL COMPILATION ===\n")
        self._append_to_log(workflow_log, "### State: final_compilation\n\n")
        
        # Final game design document compilation
        print("⏳ Project Manager: Compiling final game design documents...")
        game_design_doc = await self._compile_game_design(
            user_preferences,
            self.design_artifacts["project_plan"],
            self.design_artifacts["theme_research"],
            self.design_artifacts["mechanics_design"],
            self.design_artifacts["playtest_results"],
            self.design_artifacts["visual_design"]
        )
        
        # Save final design artifacts
        self.design_artifacts["final_design"] = game_design_doc
        
        # Save final game design document
        self._save_to_file(game_dir / "game_design_document.md", game_design_doc["content"])
        print("✅ Game design document compiled!")
        
        # Extract and save each section as a separate well-formatted HTML report
        content = game_design_doc["content"]
        
        # Extract sections using the helper method
        game_summary = self._extract_section(content, "Game Summary") or ""
        rules_content = self._extract_section(content, "Rules") or game_design_doc.get("rules", "")
        works_cited = self._extract_section(content, "Works Cited") or ""
        tester_feedback = self._extract_section(content, "Tester Feedback") or ""
        components_list_content = self._extract_section(content, "Components List") or game_design_doc.get("components", "")
        assessment = self._extract_section(content, "Assessment") or ""
        
        # Create a rules summary document if not already included
        if not rules_content:
            rules_summary = await self._create_rules_summary(game_design_doc.get("rules", ""))
            rules_content = rules_summary.get("content", "")
        
        # Create a detailed components list if not already included
        if not components_list_content:
            components_list = await self._create_detailed_components_list(game_design_doc.get("components", ""))
            components_list_content = components_list.get("content", "") if components_list else ""
        
        # Extract card image prompts from visual design
        card_prompts = ""
        if "visual_design" in self.design_artifacts and "content" in self.design_artifacts["visual_design"]:
            card_prompts = self._extract_section(self.design_artifacts["visual_design"]["content"], "Card Image Generation Prompts") or ""
        
        # Save all reports as well-formatted HTML files
        self._save_to_file(game_dir / "1_game_summary.html", game_summary)
        self._save_to_file(game_dir / "2_rules.html", rules_content)
        self._save_to_file(game_dir / "3_works_cited.html", works_cited)
        self._save_to_file(game_dir / "4_tester_feedback.html", tester_feedback)
        self._save_to_file(game_dir / "5_components_list.html", components_list_content)
        
        if card_prompts:
            self._save_to_file(game_dir / "6_card_image_prompts.html", card_prompts)
            print("✅ Card image generation prompts saved as separate HTML file!")
        
        # Save the Project Manager's assessment
        if assessment:
            self._save_to_file(game_dir / "project_manager_assessment.html", assessment)
            
            # Also add it to the workflow log
            log_file = self.log_dir / f"{user_preferences['game_name'].replace(' ', '_')}_workflow_log.md"
            self._append_to_log(log_file, f"\n## PROJECT MANAGER ASSESSMENT\n\n{assessment}")
            
        print("\n✅ All game design reports created as well-formatted HTML files!")
        print("✅ Saved: Game Summary, Rules, Works Cited, Tester Feedback, Components List, and Card Image Prompts")
        
        # Log completion
        completion_text = "### State: complete\n\n"
        
        # Return the complete game design
        return {
            "game_name": user_preferences["game_name"],
            "theme": user_preferences["theme"],
            "player_count": user_preferences["player_count"],
            "complexity": user_preferences["complexity"],
            "duration": user_preferences["duration"],
            "design_focus": user_preferences.get("design_focus", ""),
            "output_directory": str(game_dir)
        }
    
    def _append_to_log(self, log_file: Path, content: str) -> None:
        """Append content to the workflow log file."""
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(content + "\n")
    
    async def _process_current_state(self) -> None:
        """Process the current state of the workflow."""
        # Execute the appropriate method based on the current state
        if self.current_state == GameDesignState.INITIAL:
            # Initial state - create project plan
            project_plan = await self._create_project_plan(self.user_preferences)
            self.design_artifacts["project_plan"] = project_plan
            self._save_to_file(self.game_dir / "project_plan.md", project_plan["content"])
            print("✅ Project plan created!")
            
        elif self.current_state == GameDesignState.THEME_RESEARCH:
            # Theme research state
            print("⏳ Domain Scholar: Researching thematic elements...")
            theme_research = await self._research_theme(
                self.user_preferences["theme"],
                self.design_artifacts["project_plan"].get("game_concept", ""),
                self.user_preferences.get("custom_restrictions", "")
            )
            self.design_artifacts["theme_research"] = theme_research
            self._save_to_file(self.game_dir / "theme_research.md", theme_research["content"])
            print("✅ Theme research completed!")
            
        elif self.current_state == GameDesignState.MECHANIC_DESIGN:
            # Mechanic design state
            print("⏳ Gameplay Expert: Designing game mechanics...")
            
            # Check if this is a revision
            revision_prompt = ""
            if self.iteration_count[GameDesignState.MECHANIC_DESIGN] > 0:
                # This is a revision - include feedback from previous iterations
                if "playtest_results" in self.design_artifacts and self.design_artifacts["playtest_results"]:
                    revision_prompt = f"\nBased on playtest feedback: {self.design_artifacts['playtest_results'].get('content', '')[:500]}..."
                if "fact_check_results" in self.design_artifacts and self.design_artifacts["fact_check_results"]:
                    revision_prompt += f"\nBased on fact checking: {self.design_artifacts['fact_check_results'].get('content', '')[:500]}..."
            
            mechanics_design = await self._design_mechanics(
                self.design_artifacts["project_plan"].get("game_concept", ""),
                self.design_artifacts["theme_research"].get("key_elements", []),
                self.user_preferences,
                revision_prompt
            )
            self.design_artifacts["mechanics_design"] = mechanics_design
            
            # Generate a filename with iteration number
            iteration = self.iteration_count[GameDesignState.MECHANIC_DESIGN]
            self._save_to_file(self.game_dir / f"mechanics_design_v{iteration+1}.md", mechanics_design["content"])
            print(f"✅ Game mechanics designed! (Version {iteration+1})")
            
            # Extract components from mechanics
            components = await self._extract_components_from_mechanics(mechanics_design["content"])
            self.design_artifacts["components"] = components
            self._save_to_file(self.game_dir / f"components_list_v{iteration+1}.md", components["content"])
            
        elif self.current_state == GameDesignState.PLAYTEST:
            # Playtest state
            print("⏳ Test Players: Simulating gameplay and providing feedback...")
            
            # Create test player agents if not already created
            player_types = self._determine_player_types(self.user_preferences)
            self.test_players = [create_test_player_agent(player_type) for player_type in player_types]
            
            playtest_results = await self._conduct_playtests(
                self.design_artifacts["mechanics_design"].get("rules", ""),
                self.user_preferences,
                player_types
            )
            self.design_artifacts["playtest_results"] = playtest_results
            
            # Generate a filename with iteration number
            iteration = self.iteration_count[GameDesignState.PLAYTEST]
            self._save_to_file(self.game_dir / f"playtest_results_v{iteration+1}.md", playtest_results["content"])
            print(f"✅ Playtesting completed! (Version {iteration+1})")
            
        elif self.current_state == GameDesignState.FACT_CHECK:
            # Fact check state
            print("⏳ Fact Checker: Verifying thematic and mechanical accuracy...")
            
            fact_check_results = await self._fact_check(
                self.design_artifacts["theme_research"].get("content", ""),
                self.design_artifacts["mechanics_design"].get("content", ""),
                self.user_preferences["theme"]
            )
            self.design_artifacts["fact_check_results"] = fact_check_results
            
            # Generate a filename with iteration number
            iteration = self.iteration_count[GameDesignState.FACT_CHECK]
            self._save_to_file(self.game_dir / f"fact_check_report_v{iteration+1}.md", fact_check_results["content"])
            print(f"✅ Fact checking completed! (Version {iteration+1})")
            
        elif self.current_state == GameDesignState.VISUAL_DESIGN:
            # Art direction state
            print("⏳ Art Director: Creating detailed visual specifications...")
            
            # Gather all information needed for the art director
            consolidated_info = {
                "game_concept": self.design_artifacts["project_plan"].get("game_concept", ""),
                "thematic_elements": self.design_artifacts["theme_research"].get("key_elements", []),
                "mechanics": self.design_artifacts["mechanics_design"].get("content", ""),
                "components": self.design_artifacts["components"].get("content", ""),
                "fact_check": self.design_artifacts["fact_check_results"].get("content", ""),
                "theme": self.user_preferences["theme"],
                "complexity": self.user_preferences["complexity"]
            }
            
            visual_design = await self._create_detailed_visual_design(consolidated_info)
            self.design_artifacts["visual_design"] = visual_design
            
            # Save comprehensive visual design guidance
            self._save_to_file(self.game_dir / "visual_design_specifications.md", visual_design["content"])
            print("✅ Detailed visual specifications completed!")
            
            # Extract and save card image generation prompts specifically
            if "content" in visual_design:
                # Try to extract the Card Image Generation Prompts section
                card_prompts_section = self._extract_section(visual_design["content"], "Card Image Generation Prompts")
                if card_prompts_section:
                    self._save_to_file(self.game_dir / "card_image_generation_prompts.md", card_prompts_section)
                    print("✅ Card image generation prompts saved as separate file!")
            
            # Create individual component specification files
            if "component_specs" in visual_design:
                component_specs_dir = self.game_dir / "component_specifications"
                component_specs_dir.mkdir(exist_ok=True)
                
                for component_name, spec in visual_design["component_specs"].items():
                    safe_name = component_name.replace(" ", "_").replace("/", "_").lower()
                    self._save_to_file(component_specs_dir / f"{safe_name}.md", spec)
                
                print(f"✅ Individual component specifications saved to {component_specs_dir}")
    
    def _extract_text_from_agent_response(self, content: Any) -> str:
        """Extract clean text content from agent response objects."""
        if isinstance(content, str):
            return content.strip()
        
        # Handle RunResult object
        if hasattr(content, 'new_items') and content.new_items:
            # new_items is a list of MessageOutputItem
            # We concatenate the text from all items.
            return "\n".join(
                item.text.strip() for item in content.new_items if hasattr(item, "text")
            )

        # Fallback for other types
        if hasattr(content, 'text'):
            return content.text.strip()

        if hasattr(content, 'content'):
            return content.content.strip()

        # Last resort
        return str(content).strip()

    def _markdown_to_html(self, markdown_text):
        """Convert markdown text to HTML."""
        try:
            # Import markdown module
            import markdown
            from markdown.extensions.tables import TableExtension
            from markdown.extensions.fenced_code import FencedCodeExtension
            
            # Convert markdown to HTML
            html = markdown.markdown(
                markdown_text, 
                extensions=[
                    'markdown.extensions.extra',
                    'markdown.extensions.codehilite',
                    'markdown.extensions.smarty',
                    TableExtension(),
                    FencedCodeExtension()
                ]
            )
            
            # Add basic HTML styling
            styled_html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Game Design Document</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #2c3e50;
                        margin-top: 1.5em;
                        margin-bottom: 0.5em;
                    }}
                    h1 {{
                        font-size: 2.2em;
                        border-bottom: 2px solid #eaecef;
                        padding-bottom: 0.3em;
                    }}
                    h2 {{
                        font-size: 1.8em;
                        border-bottom: 1px solid #eaecef;
                        padding-bottom: 0.3em;
                    }}
                    p {{
                        margin-bottom: 1.5em;
                    }}
                    code {{
                        background-color: #f6f8fa;
                        padding: 0.2em 0.4em;
                        border-radius: 3px;
                        font-family: 'Courier New', monospace;
                    }}
                    pre {{
                        background-color: #f6f8fa;
                        padding: 16px;
                        border-radius: 6px;
                        overflow: auto;
                    }}
                    pre code {{
                        background-color: transparent;
                        padding: 0;
                    }}
                    blockquote {{
                        border-left: 4px solid #dfe2e5;
                        padding-left: 16px;
                        color: #6a737d;
                        margin-left: 0;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin-bottom: 1.5em;
                    }}
                    table, th, td {{
                        border: 1px solid #dfe2e5;
                    }}
                    th, td {{
                        padding: 8px 16px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f6f8fa;
                    }}
                    img {{
                        max-width: 100%;
                        height: auto;
                    }}
                    ul, ol {{
                        padding-left: 2em;
                        margin-bottom: 1.5em;
                    }}
                    a {{
                        color: #0366d6;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                </style>
            </head>
            <body>
                {html}
            </body>
            </html>
            '''
            
            return styled_html
        except ImportError:
            # If markdown module is not available, return the raw text as HTML
            escaped_text = markdown_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Game Design Document</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                    pre {{ white-space: pre-wrap; }}
                </style>
            </head>
            <body>
                <pre>{escaped_text}</pre>
                <p><em>Note: Install the 'markdown' package for better formatting: pip install markdown</em></p>
            </body>
            </html>
            '''

    def _save_to_file(self, filepath: Path, content: Any) -> None:
        """Save content to a file, converting to PDF if it's a markdown file."""
        clean_content = self._extract_text_from_agent_response(content)

        if filepath.suffix == '.csv':
            # Save CSV content as is
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(clean_content)
            print(f"Saved CSV file: {filepath}")
        else:
            # Assume markdown content, convert to PDF
            pdf_filepath = filepath.with_suffix('.pdf')
            
            # Convert markdown to HTML
            html_content = markdown.markdown(clean_content, extensions=['fenced_code', 'tables'])
            
            # Add some basic styling for better PDF output
            styled_html = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: sans-serif; line-height: 1.6; }}
                        h1, h2, h3 {{ color: #333; }}
                        pre {{ background-color: #f4f4f4; padding: 1em; border-radius: 5px; }}
                        code {{ font-family: monospace; }}
                        table {{ border-collapse: collapse; width: 100%; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
            </html>
            """
            
            # Create PDF from HTML
            try:
                HTML(string=styled_html).write_pdf(pdf_filepath)
                print(f"Saved PDF file: {pdf_filepath}")
            except Exception as e:
                print(f"Error creating PDF for {pdf_filepath}: {e}")
                # Fallback to saving as a markdown file
                md_filepath = filepath.with_suffix('.md')
                with open(md_filepath, "w", encoding="utf-8") as f:
                    f.write(clean_content)
                print(f"Saved markdown fallback: {md_filepath}")
            
    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a section from markdown-formatted text."""
        lines = text.split('\n')
        section_content = []
        in_section = False
        
        # Check for both # SectionName and ## SectionName formats
        section_headers = [f"# {section_name}", f"## {section_name}"]
        
        for line in lines:
            # Check if this line starts a section
            if any(line.lower().startswith(header.lower()) for header in section_headers):
                in_section = True
                section_content.append(line)
                continue
                
            # Check if we're leaving the section (next header)
            if in_section and line.startswith('#'):
                if not any(line.lower().startswith(header.lower()) for header in section_headers):
                    break
                    
            # Add lines if we're in the target section
            if in_section:
                section_content.append(line)
                
        return '\n'.join(section_content) if section_content else ''
    
    async def _generate_game_name(self, theme: str, design_focus: str) -> str:
        """Generate a game name based on theme and design focus."""
        prompt = f"""Generate a creative and marketable name for a {theme} board game 
        that focuses on {design_focus}. Provide only the name, nothing else."""
        
        result = await run_agent_with_prompt(self.project_manager, prompt, "Project Manager")
        game_name = result_text.strip().strip('"').strip("'").strip('.')
        
        # If the result has multiple lines or is very long, take just the first line or truncate
        if '\n' in game_name:
            game_name = game_name.split('\n')[0].strip()
        
        return game_name
    
    async def _create_project_plan(self, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Create an initial project plan with the Project Manager agent."""
        print("\n[STATUS] Creating project plan with Project Manager agent...")
        # Using static run_agent method instead of instantiating Runner
        
        prompt = f"""Create a comprehensive project plan for designing a board game with the following specifications:
        
        Game Name: {user_preferences.get('game_name', 'To be determined')}
        Theme: {user_preferences.get('theme', 'Not specified')}
        Player Count: {user_preferences.get('player_count', '2-4')}
        Complexity: {user_preferences.get('complexity', 'medium')}
        Duration: {user_preferences.get('duration', '30')} minutes
        Design Focus: {user_preferences.get('design_focus', 'Not specified')}
        
        Additional Requirements/Constraints:
        {user_preferences.get('custom_restrictions', 'None')}
        
        Your project plan should include:
        1. A clear game concept overview (2-3 paragraphs)
        2. Project timeline and milestones
        3. Key design challenges to address
        4. Success criteria for the game
        5. Required resources and components
        
        Format your response as a detailed Markdown document.
        """
        
        result = await run_agent_with_prompt(self.project_manager, prompt, "Project Manager")
        
        # The RunResult object structure has changed - we need to extract the text content differently
        # First, check if the result has a 'text' attribute or other content attributes
        result_text = ""
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
        
        # Log what we've found
        print(f"\n[DEBUG] RunResult structure: {dir(result)}")
        print(f"\n[DEBUG] Extracted text: {result_text[:100]}...")
        
        # Extract the game concept from the project plan (first section typically)
        content_lines = result_text.split('\n')
        game_concept = ""
        concept_found = False
        
        for line in content_lines:
            if 'game concept' in line.lower() or 'overview' in line.lower():
                concept_found = True
                continue
            if concept_found and line.startswith('#'):
                break
            if concept_found:
                game_concept += line + '\n'
        
        return {
            "content": result_text,  # Use result_text instead of result_text
            "game_concept": game_concept.strip()
        }
    
    async def _research_theme(self, theme: str, game_concept: str, custom_restrictions: str) -> Dict[str, Any]:
        """Research thematic elements with the Domain Scholar agent."""
        print("\n[STATUS] Researching theme elements with Domain Scholar agent...")
        # Using static run_agent method instead of instantiating Runner
        
        prompt = f"""As a specialist in {theme} themes, conduct comprehensive research on thematic elements 
        for a board game with the following concept:
        
        {game_concept}
        
        Additional constraints or requirements:
        {custom_restrictions}
        
        Your research should include:
        1. Historical, cultural, or conceptual background relevant to the theme
        2. Key thematic elements that could be incorporated into the game
        3. Common tropes or expectations for this theme
        4. Unique or lesser-known aspects of the theme that could make the game stand out
        5. Potential issues or sensitivities to be aware of regarding this theme
        
        Format your response as a detailed Markdown document with clear sections.
        """
        
        # Use the run_agent_with_prompt helper function for consistency
        result = await run_agent_with_prompt(self.domain_scholar, prompt, "Domain Scholar")
        
        # Extract text content from result
        result_text = ""
        if hasattr(result, 'content'):
            result_text = result_text
        elif hasattr(result, 'text'):
            result_text = result.text
        elif hasattr(result, 'new_items') and result.new_items:
            # Try to get text from new_items if it exists
            result_text = result.new_items[0].text if hasattr(result.new_items[0], 'text') else str(result.new_items[0])
        else:
            # Fallback to string representation
            result_text = str(result)
        
        # Extract key elements
        key_elements = []
        lines = result_text.split('\n')
        in_elements_section = False
        
        for line in lines:
            if 'key' in line.lower() and 'elements' in line.lower() and line.startswith('#'):
                in_elements_section = True
                continue
            if in_elements_section and line.startswith('#'):
                break
            if in_elements_section and line.strip().startswith('-'):
                key_elements.append(line.strip()[2:].strip())
        
        return {
            "content": result_text,  # Use result_text instead of result_text
            "key_elements": key_elements
        }
    
    async def _design_mechanics(self, game_concept: str, thematic_elements: List[str], user_preferences: Dict[str, Any], revision_prompt: str = "") -> Dict[str, Any]:
        """Design game mechanics based on the game concept and theme elements.
        
        Args:
            game_concept: The core concept of the game
            thematic_elements: List of thematic elements to incorporate
            user_preferences: Dictionary containing user preferences
            revision_prompt: Optional feedback from playtesting or fact checking for revisions
        
        Returns:
            Dictionary containing the mechanics design
        """
        # Prepare prompt for mechanics design
        prompt = f"""Design comprehensive game mechanics for the following board game concept:
        
        Game Concept: {game_concept}
        
        Thematic Elements: {', '.join(thematic_elements)}
        
        Player Count: {user_preferences['player_count']}
        Playing Time: {user_preferences['duration']} minutes
        Complexity Level: {user_preferences['complexity']}/10
        
        Design Focus: {user_preferences.get('design_focus', 'No specific focus')}
        
        Please provide:
        1. Core mechanics and gameplay loop
        2. Turn structure
        3. Win conditions
        4. Player interaction mechanisms
        5. Complete list of physical components needed
        6. Detailed rules explanation suitable for a rulebook
        7. Setup instructions
        8. Any variants or optional rules
        
        Important design constraints:
        - The game should be physically producible with standard board game materials
        - Rules should be clear and accessible for the target complexity level
        - The game should embody the theme in both mechanics and narrative elements
        """
        
        # Add revision instructions if this is a revision
        if revision_prompt:
            prompt += f"\n\nREVISION INSTRUCTIONS: This is a revision of previous mechanics. {revision_prompt}\n\nPlease revise the game design to address the feedback while maintaining the core concept and theme."
        
        # Run the gameplay expert agent
        # Create a Runner instance
        runner = Runner()

        # Call run on the runner instance
        result = await runner.run(self.gameplay_expert, prompt)
        
        # Extract text from the result
        result_text = ""
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
        
        # Process and structure the response
        response_text = result_text
        
        # Extract structured sections from the response
        components = {}
        if "# Components" in response_text or "## Components" in response_text:
            components_section = self._extract_section(response_text, "Components")
            components = {"raw": components_section}
        
        rules = self._extract_section(response_text, "Rules") or self._extract_section(response_text, "Game Rules") or ""
        
        # Create a more structured dictionary
        return {
            "content": response_text,
            "core_mechanics": self._extract_section(response_text, "Core Mechanics") or "",
            "turn_structure": self._extract_section(response_text, "Turn Structure") or "",
            "win_conditions": self._extract_section(response_text, "Win Conditions") or "",
            "components": components,
            "rules": rules,
            "setup": self._extract_section(response_text, "Setup") or "",
            "variants": self._extract_section(response_text, "Variants") or ""
        }
    
    async def _fact_check(self, theme_research: str, theme: str) -> Dict[str, Any]:
        """Verify the accuracy of thematic elements with the Fact Checker agent."""
        print("[STATUS] Verifying accuracy of thematic elements with Fact Checker agent...")
        
        prompt = f"""You are a diligent Fact Checker reviewing the thematic research for a board game based on the following theme: {theme}.
        
        Please carefully review the thematic research below for historical, scientific, or logical inaccuracies.
        
        THEMATIC RESEARCH:
        {theme_research}
        
        Your task is to:
        1. Identify any factual errors or inconsistencies in the thematic elements
        2. Suggest corrections for any inaccuracies found
        3. Provide additional verified facts that could enhance the thematic richness
        4. List reputable sources that support your corrections and additions
        
        IMPORTANT: At the end of your assessment, provide a numerical accuracy rating from 1-10, where:
        - 1-4: Significant factual issues that require major revisions
        - 5-7: Some factual issues that need attention
        - 8-10: Generally accurate with minor or no issues
        
        Format your response in clear sections using Markdown formatting. Begin with a summary assessment.
        Be thorough but concise, focusing on substantial issues rather than minor details.
        
        End your response with:
        ACCURACY RATING: [1-10]
        """
        
        # Use the fact_checker agent with the run_agent_with_prompt helper
        result = await run_agent_with_prompt(self.fact_checker, prompt, "Fact Checker")
        
        # Extract text from the result
        fact_check_content = self._extract_text_from_agent_response(result)
        
        # Try to extract the accuracy rating
        import re
        accuracy_rating_match = re.search(r'ACCURACY RATING:\s*(\d+(?:\.\d+)?)', fact_check_content, re.IGNORECASE)
        accuracy_rating = float(accuracy_rating_match.group(1)) if accuracy_rating_match else 0
        
        # Create enhanced theme research with fact checker inputs
        enhanced_theme_research = f"""{theme_research}

## FACT CHECKER ENHANCEMENT

{fact_check_content}"""
        
        return {
            "content": fact_check_content,
            "enhanced_theme_research": enhanced_theme_research,
            "accuracy_rating": accuracy_rating
        }
    
    async def _verify_game_elements(self, theme_research: str, mechanics_design: str, theme: str) -> Dict[str, Any]:
        """Verify the accuracy of game elements with the Fact Checker agent."""
        print("[STATUS] Verifying accuracy of game elements with Fact Checker agent...")
        
        prompt = f"""You are a diligent Fact Checker reviewing a board game design based on the following theme: {theme}.
        
        Please carefully review the thematic research and mechanics design below for historical, scientific, or logical inaccuracies.
        
        THEMATIC RESEARCH:
        {theme_research}
        
        MECHANICS DESIGN:
        {mechanics_design}
        
        Your task is to:
        1. Identify any factual errors or inconsistencies in the thematic elements
        2. Suggest corrections for any inaccuracies found
        3. Verify that the mechanics align with the thematic elements in a coherent way
        4. Provide additional verified facts that could enhance the thematic richness
        5. List reputable sources that support your corrections and additions
        
        Format your response in clear sections using Markdown formatting. Begin with a summary assessment.
        Be thorough but concise, focusing on substantial issues rather than minor details.
        """
        
        # Use the fact_checker agent with the run_agent_with_prompt helper
        result = await run_agent_with_prompt(self.fact_checker, prompt, "Fact Checker")
        
        # Extract text from the result
        fact_check_content = self._extract_text_from_agent_response(result)
        
        # Update thematic research with fact checker inputs
        enhanced_theme_research = f"""{theme_research}

## FACT CHECKER ENHANCEMENT

{fact_check_content}"""
        
        # Update the thematic research in the design artifacts
        self.design_artifacts["theme_research"]["content"] = enhanced_theme_research
        
        return {
            "content": fact_check_content,
            "enhanced_theme_research": enhanced_theme_research
        }

    
    def _determine_player_types(self, user_preferences: Dict[str, Any]) -> List[str]:
        """Determine which types of test players to create based on game requirements."""
        player_types = ["Novice Player", "Experienced Gamer"]
        
        # Add appropriate player types based on game characteristics
        complexity = user_preferences.get('complexity', 'medium')
        if complexity == 'light':
            player_types.append("Family Player")
            player_types.append("Child Player")
        elif complexity == 'heavy':
            player_types.append("Strategic Player")
            player_types.append("Competitive Player")
        
        # Handle case where design_focus might be a list or a string
        design_focus = user_preferences.get('design_focus', '')
        if isinstance(design_focus, list):
            if any('social' in item.lower() for item in design_focus if isinstance(item, str)):
                player_types.append("Social Player")
        elif isinstance(design_focus, str) and 'social' in design_focus.lower():
            player_types.append("Social Player")
        
        # Handle the theme check, which might also be a list
        theme = user_preferences.get('theme', '')
        theme_has_educational = False
        if isinstance(theme, list):
            theme_has_educational = any('educational' in item.lower() for item in theme if isinstance(item, str))
        elif isinstance(theme, str):
            theme_has_educational = 'educational' in theme.lower()
            
        # Check if either theme or design_focus contains educational
        if theme_has_educational or (
            isinstance(design_focus, list) and any('educational' in item.lower() for item in design_focus if isinstance(item, str)) or
            isinstance(design_focus, str) and 'educational' in design_focus.lower()
        ):
            player_types.append("Educational Evaluator")
        
        return player_types
    
    async def _conduct_playtests(self, rules: str, user_preferences: Dict[str, Any], player_types: List[str]) -> Dict[str, Any]:
        """Conduct simulated playtests with the Test Player agents."""
        playtest_results = []
        
        for player_type in player_types:
            print(f"  - Simulating gameplay with {player_type}...")
            test_player = create_test_player_agent(player_type)
            # Create a Runner instance without arguments
            runner = Runner()
            
            prompt = f"""You are a {player_type} playing a new board game with these specifications:
            
            Game Name: {user_preferences.get('game_name', 'Unnamed Game')}
            Theme: {user_preferences.get('theme', 'Not specified')}
            Player Count: {user_preferences.get('player_count', '2-4')}
            Complexity: {user_preferences.get('complexity', 'medium')}
            Duration: {user_preferences.get('duration', '30')} minutes
            
            The rules of the game are as follows:
            
            {rules}
            
            Simulate playing this game and provide detailed feedback from your perspective as a {player_type}.
            Your feedback should include:
            1. Your overall experience and enjoyment
            2. What aspects worked well for you
            3. What aspects were confusing or frustrating
            4. Balance issues you noticed
            5. Specific suggestions for improvement
            6. Would you play this game again? Why or why not?
            
            Format your response as a detailed Markdown document.
            """
            
            # Call run with both agent and prompt
            result = await runner.run(test_player, prompt)
            
            # Extract text from the result
            result_text = ""
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
                
            playtest_results.append({"player_type": player_type, "feedback": result_text})
        
        # Compile all playtest results into a single document
        compiled_results = "# Playtest Results\n\n"
        
        for result in playtest_results:
            compiled_results += f"## Feedback from {result['player_type']}\n\n"
            compiled_results += result['feedback'] + "\n\n"
        
        return {
            "content": compiled_results,
            "individual_results": playtest_results
        }
    
    async def _extract_components_from_mechanics(self, mechanics_content: str) -> Dict[str, Any]:
        """Extract a comprehensive components list from the mechanics design."""
        print("\n[STATUS] Extracting components list with Gameplay Expert agent...")
        # Using static run_agent method instead of instantiating Runner
        
        prompt = f"""Based on the following game mechanics design, create a comprehensive list of all physical components required for the game:
        
        {mechanics_content}
        
        Please analyze the mechanics carefully and identify ALL components that would be needed to play the game, including:
        1. Game board (if applicable)
        2. Cards (specify different types and quantities)
        3. Tokens/markers (specify different types and quantities)
        4. Dice (specify types and quantities)
        5. Player pieces/miniatures
        6. Resource tokens/cubes
        7. Reference sheets/player aids
        8. Any other physical components
        
        For each component, include:
        - Name and description
        - Approximate quantity needed
        - Size requirements (if applicable)
        - Functional requirements (how it's used in the game)
        
        Format your response as a structured Markdown document with clear sections for each component type.
        IMPORTANT: Do not include any questions or requests for more information in your response. Provide a complete components list based on the mechanics described above.
        """
        
        # Use the gameplay_expert agent instead of fact_checker
        result = await run_agent_with_prompt(self.gameplay_expert, prompt, "Gameplay Expert")

        # Extract text from the result
        result_text = ""
        if hasattr(result, "content"):
            result_text = result.content
        elif hasattr(result, "text"):
            result_text = result.text
        elif hasattr(result, "new_items") and result.new_items:
            # Try to get text from new_items if it exists
            result_text = result.new_items[0].text if hasattr(result.new_items[0], "text") else str(result.new_items[0])
        else:
            # Fallback to string representation
            result_text = str(result)

        return {
            "content": result_text
        }
    
    async def _create_detailed_visual_design(self, consolidated_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed visual specifications with the Art Director agent."""
        print("[STATUS] Creating detailed visual specifications with Art Director agent...")
        
        # Extract the enhanced thematic research that includes fact checker inputs
        thematic_elements = consolidated_info.get("thematic_elements", "")
        
        # Build the prompt for the Art Director
        prompt = f"""You are an Art Director creating detailed visual specifications for a board game.
        
        GAME CONCEPT:
        {consolidated_info.get("game_concept", "")}
        
        THEMATIC ELEMENTS (including fact checker enhancements):
        {thematic_elements}
        
        GAME MECHANICS:
        {consolidated_info.get("mechanics", "")}
        
        COMPONENTS:
        {consolidated_info.get("components", "")}
        
        THEME: {consolidated_info.get("theme", "")}
        COMPLEXITY: {consolidated_info.get("complexity", "")}
        
        Create comprehensive visual specifications for this game, including:
        
        1. OVERALL ART DIRECTION
           - Art style, color palette, and visual tone
           - Key visual themes and motifs
           - Inspirations and reference examples
        
        2. COMPONENT SPECIFICATIONS
           - Detailed visual descriptions for each game component
           - Size, material, and production recommendations
           - Layout guidelines and organizational structure
        
        3. CARD DESIGN (if applicable)
           - Card layout and structure
           - Iconography system and symbolism
           - Text formatting and readability considerations
        
        4. CARD IMAGE GENERATION PROMPTS
           - For each unique card or component type, provide a detailed image generation prompt
           - Each prompt should include style, composition, lighting, color palette and detailed visual elements
           - Make prompts specific enough to maintain consistent art style across all components
        
        Format your response as a comprehensive art direction document using Markdown.
        Be detailed and specific, focusing on actionable guidance for artists and producers.
        """
        
        # Use the art_director agent with the run_agent_with_prompt helper
        result = await run_agent_with_prompt(self.art_director, prompt, "Art Director")
        
        # Extract text from the result
        visual_design_content = self._extract_text_from_agent_response(result)
        
        # Try to extract the Card Image Generation Prompts section to save separately
        card_prompts_section = self._extract_section(visual_design_content, "CARD IMAGE GENERATION PROMPTS")
        
        # Return both the complete visual design and any extracted component specifications
        return {
            "content": visual_design_content,
            "card_prompts": card_prompts_section
        }

    
    def _extract_individual_component_specs(self, full_content: str) -> Dict[str, str]:
        """Extract individual component specifications from the full art direction document."""
        component_specs = {}
        
        # Split the content by major section headers (components)
        lines = full_content.split('\n')
        current_component = None
        current_content = []
        
        for line in lines:
            # Check if this is a major component header (usually ## or ###)
            if line.startswith('## ') and ('Box' in line or 'Board' in line or 'Card' in line or 
                                         'Token' in line or 'Miniature' in line or 'Component' in line):
                # Save the previous component if there was one
                if current_component and current_content:
                    component_specs[current_component] = '\n'.join(current_content)
                
                # Start a new component
                current_component = line.replace('#', '').strip()
                current_content = [f"# {current_component} Specifications", ""]
            elif current_component:  # We're inside a component section
                current_content.append(line)
        
        # Save the last component
        if current_component and current_content:
            component_specs[current_component] = '\n'.join(current_content)
        
        return component_specs
    
    async def _extract_components_from_mechanics(self, mechanics_content: str) -> Dict[str, Any]:
        """Extract component information from the mechanics description."""
        # Create a prompt for the Gameplay Expert to extract components
        prompt = f"""Based on the following game mechanics description, extract a complete and detailed list of all physical components required for the game. Include quantities and specifications where appropriate.
        
        MECHANICS DESCRIPTION:
        {mechanics_content[:3000]}  # Limit size for token considerations
        
        Format your response as a structured list of components, grouped by category if applicable.
        For each component, include:
        1. Name
        2. Quantity
        3. Size/dimensions (if relevant)
        4. Material/quality requirements (if relevant)
        5. Critical information that must be displayed on the component
        
        Present this as a comprehensive components manifest that could be used for production.
        """
        
        # Run the gameplay expert agent
        # Create a Runner instance
        runner = Runner()

        # Call run on the runner instance
        result = await runner.run(self.gameplay_expert, prompt)
        
        # Extract text from the result
        result_text = ""
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
        
        # Return the components list
        return {
            "content": result_text,
            "raw": result_text
        }
        
    async def _compile_game_design(self, user_preferences: Dict[str, Any], project_plan: Dict[str, Any], theme_research: Dict[str, Any], mechanics_design: Dict[str, Any], playtest_results: Dict[str, Any], visual_design: Dict[str, Any]) -> Dict[str, Any]:
        """Compile the final game design document with the Project Manager agent."""
        print("[STATUS] Compiling final game design document with Project Manager agent...")
        
        # Extract key information from each stage
        theme_elements = theme_research.get("content", "")
        mechanics = mechanics_design.get("content", "")
        visual_specs = visual_design.get("content", "")
        playtest_feedback = playtest_results.get("content", "")
        
        # Get fact check results
        fact_check_content = self.design_artifacts.get("fact_check_results", {}).get("content", "")
        
        # Build the prompt for the Project Manager
        prompt = f"""You are tasked with compiling a comprehensive game design document for a board game.
        
        Game Name: {user_preferences['game_name']}
        Theme: {user_preferences['theme']}
        Player Count: {user_preferences['player_count']}
        Complexity: {user_preferences['complexity']}
        Duration: {user_preferences['duration']} minutes
        
        Based on the following inputs from the design process, compile a well-structured game design document that includes all essential information for this game.
        
        THEMATIC ELEMENTS:
        {theme_elements}
        
        MECHANICS AND GAMEPLAY:
        {mechanics}
        
        VISUAL DESIGN SPECIFICATIONS:
        {visual_specs}
        
        PLAYTEST FEEDBACK AND ADJUSTMENTS:
        {playtest_feedback}
        
        FACT CHECK RESULTS:
        {fact_check_content}
        
        Please organize your response into the following outputs, each as a separate section:
        
        1. GAME DESIGN DOCUMENT (Main document with overview, theme, core mechanics, and components)
        2. RULES (Complete rulebook with setup, turn structure, and winning conditions)
        3. THEMATIC ELEMENTS (Key thematic elements and their integration)
        4. WORKS CITED (References and sources used)
        5. TESTER FEEDBACK (Consolidated feedback and implemented changes)
        
        Format each section as a professionally structured document. Use Markdown formatting with appropriate headers, lists, and emphasis. Be detailed yet concise, focusing on clarity and usability.
        
        For each section, also provide your assessment of whether it is sufficiently complete or needs further work.
        """
        
        # Use the project_manager agent with the run_agent_with_prompt helper
        result = await run_agent_with_prompt(self.project_manager, prompt, "Project Manager")
        
        # Extract the clean text from the result
        design_doc = self._extract_text_from_agent_response(result)
        
        # Extract individual sections
        game_design_doc = self._extract_section(design_doc, "GAME DESIGN DOCUMENT")
        rules = self._extract_section(design_doc, "RULES")
        thematic_elements = self._extract_section(design_doc, "THEMATIC ELEMENTS")
        works_cited = self._extract_section(design_doc, "WORKS CITED")
        tester_feedback = self._extract_section(design_doc, "TESTER FEEDBACK")
        
        # Extract the Project Manager's assessment
        assessment = self._extract_section(design_doc, "ASSESSMENT")
        
        # Save each section as a separate PDF/HTML file
        self._save_to_file(self.game_dir / "1_game_design_document.md", game_design_doc)
        self._save_to_file(self.game_dir / "2_rules.md", rules)
        self._save_to_file(self.game_dir / "3_thematic_elements.md", thematic_elements)
        self._save_to_file(self.game_dir / "4_works_cited.md", works_cited)
        self._save_to_file(self.game_dir / "5_tester_feedback.md", tester_feedback)
        
        # Create components list as CSV
        components = await self._create_detailed_components_list(mechanics)
        
        # Create art prompts for each component
        art_prompts = await self._create_art_generation_prompts(components, theme_research)
        
        # Save the Project Manager's assessment to the workflow log
        if assessment:
            log_file = self.log_dir / f"{user_preferences['game_name'].replace(' ', '_')}_workflow_log.md"
            self._append_to_log(log_file, f"""## PROJECT MANAGER ASSESSMENT

{assessment}""")
        
        return {
            "content": design_doc,
            "game_design_doc": game_design_doc,
            "rules": rules,
            "thematic_elements": thematic_elements,
            "works_cited": works_cited,
            "tester_feedback": tester_feedback,
            "assessment": assessment
        }


    
    async def _create_rules_summary(self, rules_content: str) -> Dict[str, Any]:
        """Create a concise rules summary from the detailed rules."""
        print("\n[STATUS] Creating rules summary with Gameplay Expert agent...")
        # Create a prompt for the Gameplay Expert to summarize rules
        prompt = f"""Create a concise, easy-to-understand summary of the following game rules. This summary should be suitable for quick reference during gameplay and cover all essential mechanics:

        {rules_content[:3000]}

        Format the summary as:
        1. Setup (brief)
        2. Core Gameplay (key actions on a turn)
        3. Win Condition (simple explanation)
        4. Key Rules to Remember

        Keep the summary to approximately 500 words total, focused on clarity and ease of understanding.
        Format your response as a well-structured Markdown document.
        """
        
        # Create a Runner instance
        runner = Runner()

        # Call run on the runner instance
        result = await runner.run(self.gameplay_expert, prompt)
        
        # Extract text from the result
        result_text = ""
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
        
        return {
            "content": result_text
        }
    
    async def _create_detailed_components_list(self, mechanics_content: str) -> Dict[str, Any]:
        """Create a detailed components list as CSV."""
        print("[STATUS] Creating detailed components list as CSV...")
        
    async def _create_art_generation_prompts(self, components: Dict[str, Any], theme_research: Dict[str, Any]) -> Dict[str, Any]:
        """Create art generation prompts for game components based on the theme."""
        print("[STATUS] Creating art generation prompts...")
        
        # Extract relevant information from the theme research
        theme_content = theme_research.get("content", "") if theme_research else ""
        
        # Get the components content
        components_content = ""
        if components is not None:
            components_content = components.get("content", "")
        
        # Create a simple prompt for each major component type
        art_prompts = {
            "box_art": f"Board game box cover art for a game with the following theme: {theme_content[:200]}...",
            "board": f"Board game main playing board based on the following theme: {theme_content[:200]}...",
            "cards": f"Card designs for a board game with the following theme: {theme_content[:200]}...",
            "tokens": f"Game tokens and pieces for a board game with the following theme: {theme_content[:200]}..."
        }
        
        # Save the prompts to a file
        prompts_text = "# Art Generation Prompts\n\n"
        for key, prompt in art_prompts.items():
            prompts_text += f"## {key.replace('_', ' ').title()}\n\n{prompt}\n\n"
        
        self._save_to_file(self.game_dir / "7_art_prompts.md", prompts_text)
        
        return {
            "content": prompts_text,
            "prompts": art_prompts
        }
        
        prompt = f"""Create a detailed, production-ready components list based on the following mechanics section:
        
        {mechanics_content}
        
        IMPORTANT: Format your response STRICTLY as a CSV table with the following columns:
        Quantity | Type | Name | Description
        
        Where:
        - Quantity: Number of this component needed
        - Type: Type of component (card, token, board, etc.)
        - Name: Specific name of the component (like card names)
        - Description: Detailed description of character, place, action, etc.
        
        Every distinct card or currency should have its own row.
        
        Start your response with the header row exactly as shown above, then list each component on its own row.
        Use pipe characters (|) to separate columns.
        DO NOT include any markdown formatting, explanations, headers, or other text - ONLY the CSV table.
        """
        
        # Use the project_manager agent with the run_agent_with_prompt helper
        result = await run_agent_with_prompt(self.project_manager, prompt, "Project Manager")
        
        # Extract the clean text from the result
        components_list = self._extract_text_from_agent_response(result)
        
        # Ensure we're only returning the CSV content, no agent metadata
        if "Quantity | Type | Name" not in components_list:
            # If the header row is missing, the response may not be in the correct format
            # Try to extract just the CSV part
            import re
            csv_match = re.search(r'(Quantity \| Type \| Name.*?)($|\n\n)', components_list, re.DOTALL)
            if csv_match:
                components_list = csv_match.group(1)
        
        # Save the components list to a CSV file
        self._save_to_file(self.game_dir / "6_components_list.csv", components_list)
        
        return {
            "content": components_list,
            "format": "csv"
        }



        # Extract text from the result
        result_text = ""
        if hasattr(result, "content"):
            result_text = result.content
        elif hasattr(result, "text"):
            result_text = result.text
        elif hasattr(result, "new_items") and result.new_items:
            # Try to get text from new_items if it exists
            result_text = result.new_items[0].text if hasattr(result.new_items[0], "text") else str(result.new_items[0])
        else:
            # Fallback to string representation
            result_text = str(result)

        return {
            "content": result_text
        }
