# Document Translator with Readability Testing

A document translation system that translates English documents to any language and ensures high readability in the target language.

## Features

- **Document Loading**: Load text from files or direct input
- **Language Selection**: Translate to any target language
- **Professional Translation**: Uses advanced LLMs for high-quality translation
- **Readability Testing**: Analyzes the readability of translated content
- **Automatic Revision**: Improves translations that don't meet readability standards

## Workflow

1. **Load Document**: The system accepts an English document (text file or direct input)
2. **Select Target Language**: Specify which language to translate into
3. **Translation**: The document is translated while preserving formatting and tone
4. **Readability Testing**: An agent analyzes the translation's readability on a scale of 1-10
5. **Revision (if needed)**: If readability score is below 7, the translation is revised
6. **Final Output**: Delivers a high-quality, readable translation

### Workflow Diagram

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

### Interactive Mode

Run the translator interactively with:

```bash
python simple_translator.py
```

### Batch Mode

Translate a file directly with:

```bash
python simple_translator.py --input sample.txt --language Spanish --output translated.txt
```

Follow the interactive prompts to:
1. Provide your document (file path or paste content)
2. Specify the target language
3. Review the translation and readability assessment

## Example

```
Assistant: Please provide the document content or a path to a text file.

You: sample.txt

Assistant: Document loaded successfully. Content preview:

# Introduction to Artificial Intelligence

Artificial Intelligence (AI) represents one of the most significant technological advancements of the modern era. It encompasses a broad range of computation...

Please specify the target language for translation.

You: French

Assistant: Target language set to: French. Starting translation process...

Assistant: Translation completed. Preview:

# Introduction à l'Intelligence Artificielle

L'Intelligence Artificielle (IA) représente l'une des avancées technologiques les plus significatives de l'ère moderne. Elle englobe un large éventail de ...

Now testing readability...

Assistant: Readability assessment:

SCORE: 8
ASSESSMENT: The text is highly informative and well-structured, making it easy to follow. The sentences are of moderate length and complexity, with a good balance between common and specialized vocabulary. The flow of ideas is coherent, and the transitions between sections are smooth.

The readability score is 8.0/10, which meets our standards. Translation is complete!

Do you want to save the translation? (y/n): y

Enter output filename: french_ai_intro.txt

Translation saved to: french_ai_intro.txt
Metadata saved to: french_ai_intro_metadata.json

Translation process completed!
```

### Revision Example

If the readability score is below 7/10, the system will automatically revise the translation:

```
Assistant: Readability assessment:

SCORE: 5.5
ASSESSMENT: The translation uses complex sentence structures and specialized terminology that may be difficult for general readers to understand. Some sentences are quite long, which affects the flow and clarity of the text.

The readability score is 5.5/10, which is below our threshold of 7/10. Revising the translation for better readability...

Assistant: Translation revised for better readability. Preview:

# Introduction à l'Intelligence Artificielle

L'Intelligence Artificielle (IA) est l'une des avancées technologiques les plus importantes de notre époque. Elle regroupe diverses techniques informatiques...

Testing readability of revised translation...

Assistant: Readability assessment:

SCORE: 8.5
ASSESSMENT: The revised translation is much more accessible. Sentences are shorter and clearer, specialized terms are explained well, and the overall flow is improved.

The readability score is 8.5/10, which meets our standards. Translation is complete!
