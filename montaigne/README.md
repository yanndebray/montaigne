# Montaigne Presentation Localization

A workflow for localizing presentation content using Google Gemini API. Generates translated images and voiceover audio from markdown scripts.

## Quick Start

```bash
# 1. Setup (install dependencies)
essai setup

# 2. Extract PDF to images
essai pdf presentation.pdf

# 3. Generate voiceover script from slides
essai script --input presentation.pdf

# 4. Generate audio from voiceover scripts
essai audio

# 5. Translate images to French
essai images

# 6. Or run full localization pipeline
essai localize --pdf presentation.pdf --lang French
```

## Prerequisites

- Python 3.10+
- Google Gemini API key

### API Key Setup

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your-api-key-here
```

Get your API key from [Google AI Studio](https://aistudio.google.com/).

## Project Structure

```
montaigne/
├── cli.py                          # Main CLI tool
├── pdf.py                          # PDF extraction
├── scripts.py                      # Script generation from slides
├── images.py                       # Image translation
├── audio.py                        # Audio generation
├── config.py                       # Configuration & dependencies
└── .env                            # API key (not committed)
```

## CLI Commands

### `setup`

Install dependencies and verify configuration.

```bash
essai setup
```

### `pdf`

Extract PDF pages to images.

```bash
essai pdf presentation.pdf
essai pdf presentation.pdf --dpi 200 --format jpg
```

### `script`

Generate voiceover scripts from PDF or slide images using AI.

```bash
# From PDF
essai script --input presentation.pdf

# From image folder
essai script --input slides_images/

# With context
essai script --input presentation.pdf --context "AI workshop for beginners"
```

### `audio`

Generate voiceover audio from markdown scripts.

```bash
# Process all voiceover scripts found in the project
essai audio

# Process a specific script
essai audio --script voiceover_script.md

# Use a different voice
essai audio --voice Kore
```

**Available voices:** Puck, Charon, Kore, Fenrir, Aoede, Orus (default)

### `images`

Translate text in images to another language.

```bash
# Auto-detect and translate images
essai images

# Translate a specific image
essai images --input slide.png

# Translate all images in a folder
essai images --input presentation_images/

# Specify output folder and target language
essai images --input slide.png --output output/ --lang Spanish
```

### `localize`

Run the full localization pipeline.

```bash
essai localize --pdf presentation.pdf --script voiceover.md --lang French
```

## Voiceover Script Format

The audio generator parses markdown files with slide-based structure:

```markdown
## SLIDE 1: Title Slide

**[Duration: ~45-60 seconds]**

Welcome to this journey into one of the most revolutionary works...

---

## SLIDE 2: Second Topic

**[Duration: ~60-75 seconds]**

Content for the second slide goes here...

---
```

### Format Requirements

- Slides start with `## SLIDE N` followed by `:` or `—` and a title
- Duration marker (`*Duration:*` or `**[Duration:]**`) signals where narration text begins
- Horizontal rules (`---`) or new slide headers end a section
- Only plain text after the duration marker is converted to speech

## Output

### Audio Files

- Format: WAV (16-bit PCM, 24kHz)
- Naming: `slide_01.wav`, `slide_02.wav`, etc.
- Location: `{script_name}_audio/` folder

### Translated Images

- Format: Same as source (or JPEG if converted)
- Naming: `{original_name}_fr.{ext}`
- Location: `images_translated/` folder (or custom via `--output`)

## API Models Used

| Task | Model |
|------|-------|
| Script Generation | `gemini-2.5-flash` |
| Image Translation | `gemini-3-pro-image-preview` |
| Audio Generation | `gemini-2.5-pro-preview-tts` |

## Troubleshooting

### Rate Limits (429 errors)

The Gemini API has rate limits. If you encounter errors:
- Wait a few minutes and retry
- Process fewer items at once
- Consider using a paid API tier

### No Slides Found

Ensure your voiceover script follows the expected format:
- Use `## SLIDE N` headers (case-insensitive)
- Include a `Duration:` line before narration text

### Image Translation Returns Text

If the model responds with text instead of generating an image:
- The prompt explicitly requests image output
- Some images may be too complex for the model
- Try with a simpler image or adjust expectations

### Package Installation Issues

If the venv has issues:

```bash
# Use system Python directly
python -m pip install google-genai python-dotenv pymupdf

# Or recreate the venv
python -m venv .venv --clear
.venv\Scripts\activate
pip install google-genai python-dotenv pymupdf
```

## Extending the Workflow

### Adding New Languages

For image translation, use the `--lang` flag:

```bash
essai images --lang German
essai images --lang Japanese
```

For audio, create a new voiceover script translated to your target language, then generate audio from it.

### Custom Voices

The Gemini TTS API supports multiple voices. Use the `--voice` parameter:

```bash
essai audio --voice Kore   # Female voice
essai audio --voice Orus   # Male voice (default)
```

## License

This project uses the Google Gemini API. Ensure compliance with [Google's Terms of Service](https://ai.google.dev/terms).
