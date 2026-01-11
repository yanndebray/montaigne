# Montaigne

Media processing toolkit for presentation localization using Google Gemini AI.

## Features

- **PDF Extraction**: Convert PDF pages to images
- **Script Generation**: Generate voiceover scripts from slides using AI
- **Image Translation**: Translate text in images to any language
- **Audio Generation**: Generate voiceover audio from scripts using TTS
- **PowerPoint Generation**: Create PPTX from PDF or images with speaker notes
- **Video Generation**: Combine slides and audio into MP4 videos

## Installation

### Using pip

```bash
pip install montaigne
```

### Using uv

```bash
uv pip install montaigne
```

### Using uvx (no installation required)

```bash
uvx --from montaigne essai setup
uvx --from montaigne essai script --input presentation.pdf
```

## Setup

1. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/)
2. Create a `.env` file:
   ```
   GEMINI_API_KEY=your-api-key
   ```
3. Verify setup:
   ```bash
   essai setup
   ```

## Usage

### Extract PDF to Images

```bash
essai pdf presentation.pdf
essai pdf presentation.pdf --dpi 200 --format jpg
```

### Generate Voiceover Script from Slides

```bash
essai script --input presentation.pdf
essai script --input slides_images/ --context "AI workshop"
essai script --input presentation.pdf --output custom_script.md
```

Options:
- `--input, -i`: PDF file or folder of slide images
- `--output, -o`: Output markdown file path
- `--context, -c`: Additional context to guide script generation. Use this to specify the topic, target audience, desired tone, or script length (e.g., "Brief scripts, 2-3 sentences per slide" or "Detailed technical explanations for developers")

### Generate Audio from Script

```bash
essai audio --script voiceover.md
essai audio --script voiceover.md --voice Kore
```

Available voices: `Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`, `Orus`

### Translate Images

```bash
essai images --input slides/
essai images --input image.png --lang Spanish
```

### Create PowerPoint from PDF or Images

```bash
essai ppt --input presentation.pdf
essai ppt --input slides/ --script voiceover.md
essai ppt --input presentation.pdf --keep-images
```

This will create a `.pptx` file with each PDF page or image as a slide. If a voiceover script is provided, it will be added as speaker notes.

### Generate Video from Slides

```bash
essai video --pdf presentation.pdf
essai video --images slides/ --audio audio/
```

### Full Localization Pipeline

```bash
essai localize --pdf presentation.pdf --script voiceover.md --lang French
```

This will:
1. Extract PDF pages to images
2. Translate all images to the target language
3. Generate audio for all slides

## Voiceover Script Format

Scripts should follow this markdown format:

```markdown
## SLIDE 1: Title
**[Duration: ~45 seconds]**

Your narration text for slide 1 goes here.

---

## SLIDE 2: Next Topic
**[Duration: ~60 seconds]**

Narration for slide 2.
```

## Demo

See the `demo/hamlet/` folder for a complete example with:
- Sample PDF presentation
- Voiceover script
- Image asset

```bash
cd demo/hamlet
essai localize --lang French
```

## Requirements

- Python 3.10+
- Google Gemini API key
- ffmpeg (for video generation)
- Dependencies: `google-genai`, `python-dotenv`, `pymupdf`, `python-pptx`, `Pillow`
