# Presentation Video Generator

Generate a narrated video from a presentation PDF with contextual voiceover scripts.

## Arguments
- `$PDF_PATH` - Path to the main presentation PDF
- `$CONTEXT_FOLDER` - Folder containing context documents (optional)
- `$MAX_DURATION` - Maximum voiceover duration per slide in seconds (default: 60)
- `$VOICE` - TTS voice to use (default: Orus)
- `$LANG` - Target language for localization (optional)

## Workflow

You are a presentation video generator assistant. Follow this workflow to create a narrated video from a presentation.

### Step 1: Analyze Input

First, identify the input files:
1. Locate the main presentation PDF at `$PDF_PATH`
2. If `$CONTEXT_FOLDER` is provided, scan it for context documents:
   - `.docx` files - Extract text content for narrative context
   - `.pdf` files - Extract and analyze slides for additional context
   - `.md` files - Read as additional context
   - `.png/.jpg` files - Note any infographics or visual references

### Step 2: Extract Context

For each context document found:

**For .docx files:**
```python
import zipfile
from xml.etree import ElementTree

with zipfile.ZipFile('document.docx', 'r') as docx:
    xml_content = docx.read('word/document.xml')
    tree = ElementTree.fromstring(xml_content)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    texts = []
    for elem in tree.iter():
        if elem.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t':
            if elem.text:
                texts.append(elem.text)
    content = ' '.join(texts)
```

**For .pdf files:**
Use `essai pdf <pdf_path>` to extract images, then analyze visually.

### Step 3: Extract Presentation Slides

Extract the main presentation to images:
```bash
essai pdf $PDF_PATH
```

This creates a folder `{pdf_stem}_images/` with `page_001.png`, `page_002.png`, etc.

Read and analyze each slide image to understand:
- Slide title and key points
- Visual elements and their meaning
- Flow and narrative progression

### Step 4: Generate Voiceover Script

Create a markdown voiceover script with this structure:

```markdown
# {Presentation Title} - Voiceover Script

## MASTER PROMPT
**IMPORTANT: Each slide voiceover MUST NOT exceed $MAX_DURATION seconds of narration.**
- Target speaking pace: 130-150 words per minute
- Maximum words per slide: ~{MAX_DURATION * 2.5} words
- Keep narration concise, impactful, and conversational

---

## SLIDE 1: {Slide Title}
**Duration:** {duration range} seconds
**Tone:** {appropriate tone}

### Voice-Over:
{Narration text that tells a compelling story, incorporating context from source documents}

---

## SLIDE 2: {Slide Title}
...
```

**Script Generation Guidelines:**
1. Use context documents to enrich narration with examples, case studies, and deeper explanations
2. Maintain narrative flow between slides
3. Match tone to slide content (inspiring for intro, practical for how-to, etc.)
4. Include specific examples and stories from context documents
5. Keep each slide under the maximum duration limit
6. End with a memorable call-to-action on the final slide

Save the script as `{pdf_stem}_voiceover.md` in the same folder as the PDF.

### Step 5: Generate Audio

Generate TTS audio from the script:
```bash
essai audio --script {pdf_stem}_voiceover.md --voice $VOICE
```

This creates `{pdf_stem}_voiceover_audio/` with `slide_01.wav`, `slide_02.wav`, etc.

### Step 6: Create Video

Combine slides and audio into a video:
```bash
essai video --pdf $PDF_PATH --audio {pdf_stem}_voiceover_audio
```

This creates the final video file.

### Step 7: Localization (Optional)

If `$LANG` is specified, also generate a localized version:

1. Translate slide images:
```bash
essai images --input {pdf_stem}_images --lang $LANG
```

2. Generate localized script (translate the voiceover script to target language)

3. Generate localized audio:
```bash
essai audio --script {pdf_stem}_voiceover_{lang}.md --voice $VOICE
```

4. Create localized video:
```bash
essai video --images {pdf_stem}_translated --audio {pdf_stem}_voiceover_{lang}_audio
```

## Output Files

The workflow produces:
- `{pdf_stem}_images/` - Extracted slide images
- `{pdf_stem}_voiceover.md` - Voiceover script
- `{pdf_stem}_voiceover_audio/` - Generated audio files
- `{pdf_stem}_video.mp4` - Final narrated video
- (If localized) `{pdf_stem}_translated/` - Translated slide images
- (If localized) `{pdf_stem}_voiceover_{lang}.md` - Translated script
- (If localized) `{pdf_stem}_{lang}_video.mp4` - Localized video

## Example Usage

Generate a video with context:
```
/presentation-video $PDF_PATH=/path/to/presentation.pdf $CONTEXT_FOLDER=/path/to/context $MAX_DURATION=60 $VOICE=Orus
```

Generate with localization:
```
/presentation-video $PDF_PATH=/path/to/deck.pdf $CONTEXT_FOLDER=/path/to/docs $LANG=French
```
