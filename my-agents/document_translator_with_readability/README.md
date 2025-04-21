# Document Translator with Readability Testing

A document translation system that translates English documents to any language and ensures high readability in the target language. This project offers two implementations: a simple state-based translator and an advanced multi-agent architecture.
### Common Features

- **Document Loading**: Load text from files or direct input
- **Language Selection**: Translate to any target language
- **Professional Translation**: Uses advanced LLMs for high-quality translation
- **Readability Testing**: Analyzes the readability of translated content
- **Automatic Revision**: Improves translations that don't meet readability standards

### Simple Translator (`simple_translator.py`)

- State machine-based workflow
- Lightweight implementation
- Sequential processing

### Multi-Agent Translator (`agent_translator.py`)

- **Supervisor-Agent Architecture**: Uses a supervisor to coordinate specialized agents
- **Specialized Agents**: Separate agents for translation, readability testing, and revision
- **Advanced Decision Making**: Dynamic workflow based on agent recommendations
- **Detailed Feedback**: More comprehensive readability assessment
- **LangGraph Integration**: Built on the LangGraph framework for agent orchestration

### Simple Translator Workflow

1. **Load Document**: The system accepts an English document (text file or direct input)
2. **Select Target Language**: Specify which language to translate into
3. **Translation**: The document is translated while preserving formatting and tone
4. **Readability Testing**: An agent analyzes the translation's readability on a scale of 1-10
5. **Revision (if needed)**: If readability score is below 7, the translation is revised
6. **Final Output**: Delivers a high-quality, readable translation
### Workflow Diagrams

#### Simple Translator Workflow

```
┌─────────┐     ┌────────────────────┐     ┌────────────────────┐     ┌─────────────────┐
│  START  │────▶│ Waiting for        │────▶│ Waiting for        │────▶│ Translating     │
└─────────┘     │ Document           │     │ Language           │     │ Document        │
                └────────────────────┘     └────────────────────┘     └─────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────┐     ┌────────────────────┐     ┌─────────────────────────┐
│  Translation    │◀────│ Revising           │◀────│ Testing                 │
│  Completed      │     │ Translation        │     │ Readability             │
└─────────────────┘     └────────────────────┘     └─────────────────────────┘
      ▲                        │                             │
      │                        │                             │
      └────────────────────────┴─────────────────────────────┘
            Score ≥ 7                       Score < 7
```

#### Multi-Agent Translator Workflow

```
                                  ┌───────────────────┐
                                  │                   │
                                  │    Supervisor     │
                                  │      Agent        │
                                  │                   │
                                  └─────────┬─────────┘
                                            │
                                            │ decides next agent
                                            ▼
          ┌─────────────────────┬───────────────────────┬─────────────────────┐
          │                     │                       │                     │
          ▼                     ▼                       ▼                     │
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐      │
│                     │ │                     │ │                     │      │
│   Translator Agent  │ │ Readability Tester  │ │    Reviser Agent    │      │
│                     │ │                     │ │                     │      │
└──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘      │
           │                       │                       │                 │
           │                       │                       │                 │
           └───────────────────────┼───────────────────────┘                 │
                                   │                                         │
                                   │ reports back                            │
                                   ▼                                         │
                          ┌─────────────────┐                                │
                          │                 │                                │
                          │   Supervisor    │◀───────────────────────────────┘
                          │     Agent       │
                          │                 │
                          └────────┬────────┘
                                   │
                                   │ if complete
                                   ▼
                          ┌─────────────────┐
                          │                 │
                          │      END        │
                          │                 │
                          └─────────────────┘
```
### Multi-Agent Translator Workflow

1. **Load Document & Language**: The system accepts an English document and target language
2. **Supervisor Agent**: Coordinates the workflow and decides which agent to call next
3. **Translator Agent**: Specialized agent for high-quality translation
4. **Readability Tester Agent**: Dedicated agent for comprehensive readability assessment
5. **Reviser Agent**: Specialized agent for improving translations with low readability
6. **Dynamic Workflow**: The supervisor makes decisions based on each agent's output
7. **Final Output**: Delivers a high-quality, readable translation with detailed feedback

## Requirements

- Python 3.8+
- OpenAI API key (for GPT models)

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

## Usage

### Simple Translator

#### Interactive Mode

Run the simple translator interactively with:

```bash
python simple_translator.py
```

#### Batch Mode

Translate a file directly with:

```bash
python simple_translator.py --input sample.txt --language Spanish --output translated.txt
```

### Multi-Agent Translator

The multi-agent translator uses a supervisor-agent architecture for more sophisticated translation workflow.

#### Interactive Mode

Run the multi-agent translator interactively with:

```bash
python agent_translator.py
```

#### Batch Mode

Translate a file directly with:

```bash
python agent_translator.py --input sample.txt --language Spanish --output translated.txt
```

Follow the interactive prompts to:
1. Provide your document (file path or paste content)
2. Specify the target language
3. Review the translation and readability assessment

## Examples

### Example 1: Translation to Another Language

```
Assistant: Please provide the document content or a path to a text file.

You: sample.txt

Assistant: Document loaded successfully. Content preview:

# Introduction to Artificial Intelligence

Artificial Intelligence (AI) represents one of the most significant technological advancements of the modern era. It encompasses a broad range of computation...

Assistant: Please specify the target language for translation.

You: French

Assistant: Target language set to: French. Starting translation process...

Assistant: Translation completed. Preview:

# Introduction à l'Intelligence Artificielle

L'Intelligence Artificielle (IA) représente l'une des avancées technologiques les plus significatives de l'ère moderne. Elle englobe un large éventail de ...

Assistant: Now testing readability...

Assistant: Readability assessment:

SCORE: 8
ASSESSMENT: The text is highly informative and well-structured, making it easy to follow. The sentences are of moderate length and complexity, with a good balance between common and specialized vocabulary. The flow of ideas is coherent, and the transitions between sections are smooth.

The readability score is 8.0/10, which meets our standards. Translation is complete!

Assistant: Metadata saved to: french_ai_intro_metadata.json

Assistant: Translation process completed!
```

### Example 2: Improving Readability of English Text

The system can also be used to improve the readability of text that's already in the target language. This is useful for simplifying complex or poorly written content.

```bash
python agent_translator.py --input poor_sample.txt --language English
```

Output:

```
================================================================================
🚀 STARTING TRANSLATION WORKFLOW
📄 Input file: poor_sample.txt
🌐 Target language: English
================================================================================
✅ Document loaded: 3773 characters

Log file will be saved to: poor_sample_English_2025_04_21.txt

================================================================================
🧠 SUPERVISOR AGENT: Deciding next step...
--------------------------------------------------------------------------------
🔍 Checking if document is already in English...
✅ Document is already in English, skipping translation

================================================================================
📊 READABILITY TESTER AGENT: Assessing English translation...
--------------------------------------------------------------------------------
📝 Analyzing readability...
✅ ASSESSMENT COMPLETE: Readability score = 5.0/10
📝 FEEDBACK:
Score: 5/10

**Assessment:**
The text is dense and uses highly complex, academic language that reduces clarity.
⚠️ REVISION NEEDED: Score below threshold of 7.0

================================================================================
🧠 SUPERVISOR AGENT: Deciding next step...
--------------------------------------------------------------------------------
✅ DECISION: Call the reviser agent
📝 REASON: The document is already in English, has a readability score of 5.0, and revision is needed to improve readability.

================================================================================
✏️ REVISER AGENT: Improving English translation...
--------------------------------------------------------------------------------
📝 Current readability score: 5.0/10
📝 Revising translation to improve readability...
✅ REVISION COMPLETE: Translation revised for better readability

================================================================================
📊 READABILITY TESTER AGENT: Assessing English translation...
--------------------------------------------------------------------------------
📝 Analyzing readability...
✅ ASSESSMENT COMPLETE: Readability score = 9.0/10
📝 FEEDBACK:
Score: 9/10
✅ NO REVISION NEEDED: Score meets or exceeds threshold of 7.0

================================================================================
🧠 SUPERVISOR AGENT: Deciding next step...
--------------------------------------------------------------------------------
✅ DECISION: Call the FINISH agent
📝 REASON: The document is in English, has a high readability score (9.0), and no further revision is needed.

================================================================================
🎉 WORKFLOW COMPLETE: Translation process finished successfully
================================================================================
Translation saved to: poor_sample_English.txt
Metadata saved to: poor_sample_English_metadata.json

================================================================================
📊 FINAL RESULTS:
✅ Translation saved to: poor_sample_English.txt
📊 Readability score: 9.0/10
🔄 Note: The translation was revised to improve readability (from 5.0/10 to 9.0/10).
================================================================================

Log saved to: poor_sample_English_2025_04_21.txt
```

## Output Files

The translator generates several output files:

1. **Translation File**: Contains the translated or revised content
   - Example: `poor_sample_English.txt`

2. **Metadata File**: JSON file with information about the translation
   - Example: `poor_sample_English_metadata.json`
   - Contains:
     - Target language
     - Readability score
     - Whether revisions were made

   ```json
   {
     "target_language": "English",
     "readability_score": 9.0,
     "revisions_made": true
   }
   ```

3. **Log File**: Detailed log of the entire translation process
   - Example: `poor_sample_English_2025_04_21.txt`
   - Naming format: `{input_file}_{language}_{yyyy_mm_dd}.txt`
   - Contains all terminal output including:
     - Agent decisions and reasoning
     - Readability assessments
     - Revision details
     - Error messages (if any)

## Sample Files

The repository includes these sample files:

1. **sample.txt**: A well-written sample document for testing translations

2. **poor_sample.txt**: A poorly written English document with low readability
   - Use this to test the readability improvement feature
   - Run with: `python agent_translator.py --input poor_sample.txt --language English`
   - The system will detect it's already in English and focus on improving readability
