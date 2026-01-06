# Kant

Media processing toolkit for presentation localization using Google Gemini AI.

## Features

- **PDF Extraction**: Convert PDF pages to images
- **Image Translation**: Translate text in images to any language
- **Audio Generation**: Generate voiceover audio from scripts using TTS

## Installation

```bash
pip install -e .
```

## Setup

1. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/)
2. Create a `.env` file:
   ```
   GEMINI_API_KEY=your-api-key
   ```
3. Verify setup:
   ```bash
   kant setup
   ```

## Usage

### Extract PDF to Images

```bash
kant pdf presentation.pdf
kant pdf presentation.pdf --dpi 200 --format jpg
```

### Generate Audio from Script

```bash
kant audio --script voiceover.md
kant audio --script voiceover.md --voice Kore
```

Available voices: `Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`, `Orus`

### Translate Images

```bash
kant images --input slides/
kant images --input image.png --lang Spanish
```

### Full Localization Pipeline

```bash
kant localize --pdf presentation.pdf --script voiceover.md --lang French
```

This will:
1. Extract PDF pages to images
2. Translate all images to the target language
3. Generate audio for all slides

## Voiceover Script Format

Scripts should follow this markdown format:

```markdown
## SLIDE 1: Title
**Duration: ~45 seconds**

Your narration text for slide 1 goes here.

---

## SLIDE 2: Next Topic
**Duration: ~60 seconds**

Narration for slide 2.
```

## Demo

See the `demo/hamlet/` folder for a complete example with:
- Sample PDF presentation
- Voiceover script
- Image asset

```bash
cd demo/hamlet
kant localize --lang French
```

## Requirements

- Python 3.10+
- Google Gemini API key
- Dependencies: `google-genai`, `python-dotenv`, `pymupdf`
