# Document Translator with Readability Testing

A multi-agent document translation system that translates documents between languages while ensuring high readability in the target language. This project offers multiple implementations with different model providers and architectures.
## Available Implementations

| Implementation | File | Description | Models |
|----------------|------|-------------|--------|
| Simple Translator | `simple_translator.py` | State machine-based workflow with sequential processing | OpenAI |
| Multi-Agent Translator | `agent_translator.py` | Supervisor-agent architecture with specialized agents | OpenAI |
| Novita.ai Multi-Agent Translator | `novita_agent_translator.py` | Multi-agent architecture using open source models | Novita.ai |

## Key Features

- **Multi-Agent Architecture**: Specialized agents for translation, readability assessment, and revision
- **Readability Testing**: Analyzes and scores translations on a 1-10 scale
- **Automatic Revision**: Improves translations with readability scores below 7/10
- **Multiple Model Options**: Support for both OpenAI and Novita.ai open source models
- **Batch & Interactive Modes**: Process files directly or through interactive prompts
- **Detailed Logging**: Comprehensive logs of the translation process

## Translation Workflow

1. **Document Input**: Load text from a file or direct input
2. **Language Selection**: Specify the target language
3. **Translation**: Convert the document to the target language
4. **Readability Assessment**: Score the translation's readability (1-10 scale)
5. **Revision (if needed)**: Improve translations scoring below 7/10
6. **Final Output**: Deliver the completed translation with metadata
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
## Multi-Agent Architecture

| Agent | Role | OpenAI Model | Novita.ai Model |
|-------|------|--------------|----------------|
| **Supervisor** | Coordinates workflow and decides next steps | GPT-4 | Mistral 7B |
| **Translator** | Performs high-quality translation | GPT-4 | Llama 3 70B |
| **Readability Tester** | Assesses translation quality on a 1-10 scale | GPT-4 | Mistral 7B |
| **Reviser** | Improves translations with low readability | GPT-4 | Qwen 2.5 7B |

## Requirements

- Python 3.8+
- API keys (based on implementation choice)

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```
   # For OpenAI implementations
   OPENAI_API_KEY=your_openai_api_key
   
   # For Novita.ai implementation
   NOVITA_API_KEY=your_novita_api_key
   ```

## Usage

### OpenAI Implementations

```bash
# Simple Translator (Interactive)
python simple_translator.py

# Simple Translator (Batch)
python simple_translator.py --input sample.txt --language Spanish

# Multi-Agent Translator (Interactive)
python agent_translator.py

# Multi-Agent Translator (Batch)
python agent_translator.py --input sample.txt --language Spanish
```

### Novita.ai Implementation

```bash
# Novita.ai Multi-Agent Translator (Interactive)
python novita_agent_translator.py

# Novita.ai Multi-Agent Translator (Batch)
python novita_agent_translator.py --input sample.txt --language Spanish
```

## Output Files

All implementations generate the following output files:

- `{input_filename}_{target_language}.txt` - The translated document
- `{input_filename}_{target_language}_metadata.json` - Metadata including readability scores
- `{input_filename}_{target_language}_{date}.txt` - Detailed log of the translation process

## Novita.ai Integration

The `novita_agent_translator.py` implementation uses open source models from Novita.ai:

### Features

- **Open Source Models**: Uses Llama 3, Mistral, and Qwen models via Novita.ai's API
- **Model Specialization**: Each agent uses a model optimized for its specific task
- **Robust Error Handling**: Improved readability assessment and loop prevention
- **Detailed Logging**: Shows which model is handling each part of the workflow

### Configuration

The Novita.ai implementation requires a valid Novita.ai API key in your `.env` file:

```
NOVITA_API_KEY=your_novita_api_key
```

### Example Output

```
================================================================================
🧠 SUPERVISOR AGENT (MISTRAL-7B-INSTRUCT): Deciding next step...
--------------------------------------------------------------------------------
✅ LOGICAL DECISION: Call the translator agent
📝 REASON: We have document content and target language but no translation yet.
================================================================================

================================================================================
🐤 TRANSLATOR AGENT (LLAMA-3-70B-INSTRUCT): Translating document to Spanish...
--------------------------------------------------------------------------------
📝 Processing document (2712 characters)...
✅ TRANSLATION COMPLETE: Document translated to Spanish
================================================================================

================================================================================
📊 READABILITY TESTER AGENT (MISTRAL-7B-INSTRUCT): Assessing Spanish translation...
--------------------------------------------------------------------------------
📝 Analyzing readability...
✅ ASSESSMENT COMPLETE: Readability score = 8.0/10
================================================================================
```

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
