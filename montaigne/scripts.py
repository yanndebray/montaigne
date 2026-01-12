"""Script generation from PDF slides using Gemini AI."""

import mimetypes
import sys
from pathlib import Path
from typing import List, Optional

from .config import get_gemini_client

IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png", ".gif", ".webp"}
SCRIPT_MODEL = "gemini-3-pro-preview"


def _get_arc_position(slide_num: int, total: int) -> str:
    """Determine narrative position for tone guidance.

    Args:
        slide_num: Current slide number (1-indexed)
        total: Total number of slides

    Returns:
        Description of the narrative position and suggested tone
    """
    if total <= 1:
        return "Single slide - comprehensive overview"

    progress = slide_num / total
    if progress <= 0.15:
        return "Opening - set the stage, build anticipation, inviting tone"
    elif progress <= 0.25:
        return "Problem/motivation - energetic, problem-aware, solution-oriented"
    elif progress <= 0.75:
        return "Body - technical, instructional, practical, example-driven"
    elif progress <= 0.90:
        return "Synthesis - analytical, decision-supporting, consolidating"
    else:
        return "Closing - inspiring, forward-looking, call to action"


def analyze_presentation_overview(images: List[Path], context: str = "", client=None) -> dict:
    """
    First pass: analyze all slides to create a presentation overview.

    This provides holistic context for generating coherent, connected scripts.

    Args:
        images: List of paths to slide images
        context: Optional user-provided context about the presentation
        client: Optional pre-configured Gemini client

    Returns:
        Dict with keys:
        - topic: Main presentation topic
        - audience: Inferred target audience
        - tone: Suggested overall tone
        - total_duration: Estimated total duration
        - slide_summaries: List of brief summaries for each slide
        - terminology: List of technical terms for pronunciation guide
    """
    from google.genai import types

    if client is None:
        client = get_gemini_client()

    # Prepare images for the API - use a subset if too many slides
    max_slides_for_overview = 15
    sample_images = images[:max_slides_for_overview]

    image_parts = []
    for img_path in sample_images:
        with open(img_path, "rb") as f:
            image_data = f.read()
        mime_type, _ = mimetypes.guess_type(str(img_path))
        if mime_type is None:
            mime_type = "image/png"
        image_parts.append(types.Part.from_bytes(mime_type=mime_type, data=image_data))

    context_note = f"\nUser-provided context: {context}" if context else ""

    prompt = f"""Analyze this presentation (all {len(images)} slides shown) and provide a comprehensive overview.
{context_note}

Please analyze and respond in this EXACT format:

TOPIC: [Main topic/title of the presentation in 5-10 words]

AUDIENCE: [Target audience - e.g., "Developers and data scientists", "Business executives", "Technical managers"]

TONE: [Overall tone - e.g., "Technical but accessible, practical and empowering"]

TOTAL_DURATION: [Estimated total voiceover duration for all slides, e.g., "12-15 minutes"]

SLIDE_SUMMARIES:
1. [Brief 5-10 word summary of slide 1's main point]
2. [Brief 5-10 word summary of slide 2's main point]
... [continue for all slides]

TERMINOLOGY: [Comma-separated list of technical terms, library names, acronyms that need pronunciation guidance]

NARRATIVE_NOTES: [2-3 sentences about the narrative arc - how the presentation flows from introduction through body to conclusion]"""

    contents = [
        types.Content(
            role="user",
            parts=image_parts + [types.Part.from_text(text=prompt)],
        ),
    ]

    response = client.models.generate_content(
        model=SCRIPT_MODEL,
        contents=contents,
    )

    text = response.text

    # Parse the response
    overview = {
        "topic": "Presentation",
        "audience": "General audience",
        "tone": "Professional and informative",
        "total_duration": f"{len(images) * 1}-{len(images) * 2} minutes",
        "slide_summaries": [f"Slide {i+1}" for i in range(len(images))],
        "terminology": [],
        "narrative_notes": "",
    }

    # Extract each field
    if "TOPIC:" in text:
        overview["topic"] = text.split("TOPIC:")[1].split("\n")[0].strip()

    if "AUDIENCE:" in text:
        overview["audience"] = text.split("AUDIENCE:")[1].split("\n")[0].strip()

    if "TONE:" in text:
        overview["tone"] = text.split("TONE:")[1].split("\n")[0].strip()

    if "TOTAL_DURATION:" in text:
        overview["total_duration"] = text.split("TOTAL_DURATION:")[1].split("\n")[0].strip()

    if "SLIDE_SUMMARIES:" in text:
        summaries_section = text.split("SLIDE_SUMMARIES:")[1]
        # Find where the next section starts
        end_markers = ["TERMINOLOGY:", "NARRATIVE_NOTES:"]
        for marker in end_markers:
            if marker in summaries_section:
                summaries_section = summaries_section.split(marker)[0]

        # Parse numbered list
        summaries = []
        for line in summaries_section.strip().split("\n"):
            line = line.strip()
            if line and line[0].isdigit():
                # Remove the number prefix (e.g., "1. ", "12. ")
                parts = line.split(".", 1)
                if len(parts) > 1:
                    summaries.append(parts[1].strip())
                else:
                    summaries.append(line)
        if summaries:
            overview["slide_summaries"] = summaries

    if "TERMINOLOGY:" in text:
        term_line = text.split("TERMINOLOGY:")[1].split("\n")[0].strip()
        if "NARRATIVE_NOTES:" in term_line:
            term_line = term_line.split("NARRATIVE_NOTES:")[0].strip()
        overview["terminology"] = [t.strip() for t in term_line.split(",") if t.strip()]

    if "NARRATIVE_NOTES:" in text:
        overview["narrative_notes"] = text.split("NARRATIVE_NOTES:")[1].strip().split("\n\n")[0]

    # Pad summaries if we have fewer than total slides
    while len(overview["slide_summaries"]) < len(images):
        overview["slide_summaries"].append(f"Slide {len(overview['slide_summaries']) + 1}")

    return overview


def generate_slide_script(
    image_path: Path,
    slide_number: int = 1,
    context: str = "",
    client=None,
    total_slides: int = 1,
    previous_summary: str = "",
    upcoming_preview: str = "",
    presentation_overview: Optional[dict] = None,
) -> dict:
    """
    Generate a voiceover script for a single slide image using Gemini.

    Args:
        image_path: Path to the slide image
        slide_number: Slide number for the script header
        context: Optional context about the presentation
        client: Optional pre-configured Gemini client
        total_slides: Total number of slides in the presentation
        previous_summary: Brief summary of the previous slide's content
        upcoming_preview: Brief preview of the next slide's topic
        presentation_overview: Dict from analyze_presentation_overview() with
            topic, audience, tone, and other holistic context

    Returns:
        Dict with 'number', 'title', 'duration', 'tone', and 'text' keys
    """
    from google.genai import types

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if client is None:
        client = get_gemini_client()

    # Read source image
    with open(image_path, "rb") as f:
        image_data = f.read()

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/png"

    # Build enhanced context from overview
    if presentation_overview:
        topic = presentation_overview.get("topic", "Presentation")
        audience = presentation_overview.get("audience", "General audience")
        tone = presentation_overview.get("tone", "Professional and informative")
    else:
        topic = "Presentation"
        audience = "General audience"
        tone = "Professional and informative"

    arc_position = _get_arc_position(slide_number, total_slides)

    # Build context sections
    context_parts = []
    if context:
        context_parts.append(f"User-provided context: {context}")

    prev_context = previous_summary if previous_summary else "This is the first slide"
    next_context = upcoming_preview if upcoming_preview else "This is the final slide"

    prompt = f"""Analyze this presentation slide and generate a voiceover script.

PRESENTATION CONTEXT:
- Topic: {topic}
- Target Audience: {audience}
- Overall Tone: {tone}
- This is slide {slide_number} of {total_slides}
- Narrative position: {arc_position}
{chr(10).join(context_parts)}

PREVIOUS SLIDE: {prev_context}
NEXT SLIDE: {next_context}

Please provide:
1. TITLE: A short title for this slide (max 50 characters)
2. TONE: Suggested tone for this specific slide (e.g., "inviting, setting the stage" or "technical, instructional")
3. DURATION: Estimated speaking duration (e.g., "45-60 seconds")
4. SCRIPT: A natural, conversational voiceover script that:
   - Creates a smooth transition from the previous content (if not the first slide)
   - Uses conversational, engaging language appropriate for {audience}
   - Includes rhetorical questions where appropriate to engage the audience
   - Uses emphasis markers (*word*) for key terms when first introduced
   - Does NOT simply read bullet points verbatim - expand and explain
   - Sets up or foreshadows the next slide when appropriate (if not the last slide)
   - Matches the narrative position: {arc_position}

Format your response EXACTLY as:
TITLE: [slide title]
TONE: [tone for this slide]
DURATION: [estimated duration]
SCRIPT:
[voiceover text here]"""

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(mime_type=mime_type, data=image_data),
                types.Part.from_text(text=prompt),
            ],
        ),
    ]

    response = client.models.generate_content(
        model=SCRIPT_MODEL,
        contents=contents,
    )

    # Parse response
    text = response.text

    title = f"Slide {slide_number}"
    slide_tone = "Professional"
    duration = "30-45 seconds"
    script = text

    # Extract title
    if "TITLE:" in text:
        title_line = text.split("TITLE:")[1].split("\n")[0].strip()
        title = title_line[:50] if title_line else title

    # Extract tone
    if "TONE:" in text:
        tone_line = text.split("TONE:")[1].split("\n")[0].strip()
        slide_tone = tone_line if tone_line else slide_tone

    # Extract duration
    if "DURATION:" in text:
        duration_line = text.split("DURATION:")[1].split("\n")[0].strip()
        duration = duration_line if duration_line else duration

    # Extract script
    if "SCRIPT:" in text:
        script = text.split("SCRIPT:")[1].strip()

    return {
        "number": slide_number,
        "title": title,
        "tone": slide_tone,
        "duration": duration,
        "text": script,
    }


def generate_scripts(
    input_path: Path, output_path: Optional[Path] = None, context: str = ""
) -> Path:
    """
    Generate voiceover scripts from PDF or image folder.

    Uses a two-pass approach:
    1. First pass: Analyze all slides for holistic context (topic, audience, tone, summaries)
    2. Second pass: Generate individual scripts with sliding window context

    Args:
        input_path: PDF file or directory containing slide images
        output_path: Path for output markdown file (default: {input_stem}_voiceover.md)
        context: Optional context about the presentation

    Returns:
        Path to generated markdown script file
    """
    from .pdf import extract_pdf_pages

    input_path = Path(input_path)

    # Handle PDF input
    if input_path.suffix.lower() == ".pdf":
        print(f"Extracting pages from PDF: {input_path.name}")
        images_dir = input_path.parent / f"{input_path.stem}_images"
        images = extract_pdf_pages(input_path, output_dir=images_dir)
        base_name = input_path.stem
    elif input_path.is_dir():
        images = sorted([f for f in input_path.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS])
        base_name = input_path.name
    elif input_path.is_file() and input_path.suffix.lower() in IMAGE_EXTENSIONS:
        images = [input_path]
        base_name = input_path.stem
    else:
        raise FileNotFoundError(f"Input not found or unsupported: {input_path}")

    if not images:
        raise ValueError(f"No images found in {input_path}")

    # Determine output path
    if output_path is None:
        output_path = input_path.parent / f"{base_name}_voiceover.md"
    output_path = Path(output_path)

    client = get_gemini_client()
    total_slides = len(images)

    # === PASS 1: Analyze presentation overview ===
    print(f"\n[Pass 1/2] Analyzing presentation overview ({total_slides} slides)...")
    try:
        overview = analyze_presentation_overview(images, context=context, client=client)
        print(f"  Topic: {overview['topic']}")
        print(f"  Audience: {overview['audience']}")
        print(f"  Tone: {overview['tone']}")
    except Exception as e:
        print(f"  Warning: Overview analysis failed ({e}), using defaults")
        overview = {
            "topic": base_name.replace("_", " ").title(),
            "audience": "General audience",
            "tone": "Professional and informative",
            "total_duration": f"{total_slides}-{total_slides * 2} minutes",
            "slide_summaries": [f"Slide {i+1}" for i in range(total_slides)],
            "terminology": [],
            "narrative_notes": "",
        }

    # === PASS 2: Generate individual scripts with context ===
    print(f"\n[Pass 2/2] Generating scripts for {total_slides} slide(s)...")
    slides_data = []

    # Use tqdm for progress bar if available in TTY environment
    try:
        from tqdm import tqdm

        use_tqdm = sys.stderr.isatty()
    except ImportError:
        use_tqdm = False

    # Create the base iterator
    if use_tqdm:
        image_iterator = tqdm(
            enumerate(images, 1), total=len(images), desc="Generating scripts", unit="slide"
        )
    else:
        image_iterator = enumerate(images, 1)

    for i, image_path in image_iterator:
        if not use_tqdm:
            print(f"  Slide {i}/{total_slides}: {image_path.name}...")

        # Build sliding window context
        previous_summary = ""
        upcoming_preview = ""

        if i > 1 and len(overview["slide_summaries"]) >= i - 1:
            previous_summary = overview["slide_summaries"][i - 2]  # Previous slide (0-indexed)

        if i < total_slides and len(overview["slide_summaries"]) >= i + 1:
            upcoming_preview = overview["slide_summaries"][i]  # Next slide (0-indexed)

        try:
            slide_data = generate_slide_script(
                image_path,
                slide_number=i,
                context=context,
                client=client,
                total_slides=total_slides,
                previous_summary=previous_summary,
                upcoming_preview=upcoming_preview,
                presentation_overview=overview,
            )
            slides_data.append(slide_data)
            if not use_tqdm:
                print(f"    [OK] {slide_data['title'][:40]}...")
        except Exception as e:
            if not use_tqdm:
                print(f"    [ERROR] {e}")
            slides_data.append(
                {
                    "number": i,
                    "title": f"Slide {i}",
                    "tone": "Professional",
                    "duration": "30 seconds",
                    "text": f"[Script generation failed: {e}]",
                }
            )

    # === Generate production notes ===
    print("\nGenerating production notes...")
    production_notes = _generate_production_notes(
        terminology=overview.get("terminology", []), slides=slides_data, overview=overview
    )

    # === Format and save output ===
    markdown = _format_scripts_markdown(
        slides=slides_data,
        title=overview.get("topic", base_name),
        overview=overview,
        production_notes=production_notes,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\nGenerated voiceover script: {output_path}")
    print(f"  Word count: ~{production_notes['word_count']:,}")
    print(f"  Estimated duration: {production_notes['estimated_duration']}")
    return output_path


def _generate_production_notes(terminology: List[str], slides: List[dict], overview: dict) -> dict:
    """
    Generate production notes including pronunciation guide.

    Args:
        terminology: List of technical terms from overview
        slides: List of slide data dicts
        overview: Presentation overview dict

    Returns:
        Dict with 'pronunciation', 'delivery', and 'music' keys
    """
    # Common pronunciation rules for technical terms
    pronunciation_rules = {
        "python-pptx": "python p-p-t-x",
        "pptxgenjs": "p-p-t-x gen J-S",
        "reveal.js": "reveal dot J-S",
        "ooxml": "O-O-X-M-L",
        "oauth": "O-Auth (rhymes with oath)",
        "pydantic": "pie-dan-tic",
        "api": "A-P-I",
        "json": "JAY-son",
        "yaml": "YAM-el",
        "sql": "S-Q-L or sequel",
        "cli": "C-L-I",
        "gui": "G-U-I or gooey",
        "async": "A-sink",
        "npm": "N-P-M",
        "nodejs": "node J-S",
        "css": "C-S-S",
        "html": "H-T-M-L",
        "pdf": "P-D-F",
        "llm": "L-L-M",
        "ai": "A-I",
        "url": "U-R-L",
        "http": "H-T-T-P",
        "https": "H-T-T-P-S",
        "cdn": "C-D-N",
        "react": "react (as spelled)",
        "angular": "angular (as spelled)",
        "electron": "electron (as spelled)",
        "typescript": "typescript (as spelled)",
        "javascript": "javascript (as spelled)",
        "dataframe": "data-frame",
        "pandas": "pandas (like the animal)",
        "matplotlib": "mat-plot-lib",
        "numpy": "num-pie",
        "scipy": "sigh-pie",
    }

    # Generate pronunciation guide from terminology
    pron_lines = []
    for term in terminology:
        term_lower = term.lower().replace(" ", "").replace("-", "")
        # Check if we have a known pronunciation
        for key, pron in pronunciation_rules.items():
            if key.replace("-", "").replace(".", "") in term_lower or term_lower in key.replace(
                "-", ""
            ).replace(".", ""):
                pron_lines.append(f'- `{term}`: "{pron}"')
                break
        else:
            # If not found, add the term as-is for manual review
            if any(c.isupper() for c in term) or "." in term or "-" in term:
                pron_lines.append(f"- `{term}`: [verify pronunciation]")

    # Calculate total word count and duration
    total_words = sum(len(slide.get("text", "").split()) for slide in slides)
    # Average speaking pace: 130-150 words per minute
    min_duration = total_words // 150
    max_duration = total_words // 130

    return {
        "pronunciation": (
            "\n".join(pron_lines) if pron_lines else "No special pronunciations noted."
        ),
        "word_count": total_words,
        "estimated_duration": f"{min_duration}-{max_duration} minutes",
        "delivery": """- Maintain a steady, confident pace throughout
- Allow brief pauses (0.5-1 second) between major sections within each slide
- Emphasize key terms on first introduction (marked with *italics* in script)
- Code references and library names should be pronounced clearly and distinctly""",
        "music": """- Opening slides: Subtle, building anticipation
- Body/technical slides: Steady, focused energy
- Synthesis slides: Practical, grounded
- Closing slide: Inspiring, resolving""",
    }


def _format_scripts_markdown(
    slides: List[dict],
    title: str,
    overview: Optional[dict] = None,
    production_notes: Optional[dict] = None,
) -> str:
    """
    Format slide scripts as markdown with rich metadata.

    Args:
        slides: List of slide data dicts
        title: Presentation title
        overview: Optional presentation overview dict
        production_notes: Optional production notes dict

    Returns:
        Formatted markdown string
    """
    # Header with metadata
    lines = [f"# {title}", "## Voice-Over Script", ""]

    # Add overview metadata if available
    if overview:
        lines.extend(
            [
                f"**Total Duration:** ~{overview.get('total_duration', 'Unknown')}",
                f"**Target Audience:** {overview.get('audience', 'General audience')}",
                f"**Tone:** {overview.get('tone', 'Professional')}",
                "",
            ]
        )
    else:
        lines.extend([f"**Total slides:** {len(slides)}", ""])

    lines.extend(["---", ""])

    # Individual slides
    for slide in slides:
        lines.extend(
            [
                f"## Slide {slide['number']}: {slide['title']}",
                f"**Duration:** {slide.get('duration', '30-45 seconds')}",
            ]
        )

        # Add tone if available
        if slide.get("tone"):
            lines.append(f"**Tone:** {slide['tone']}")

        lines.extend(
            ["", "### Voice-Over:", "", slide.get("text", "[No script generated]"), "", "---", ""]
        )

    # Add production notes section if available
    if production_notes:
        lines.extend(
            [
                "## Production Notes",
                "",
                "### General Guidance",
                production_notes.get("delivery", ""),
                "",
                "### Estimated Reading Time",
                f"- **Word count:** ~{production_notes.get('word_count', 0):,} words",
                f"- **Duration at presentation pace:** {production_notes.get('estimated_duration', 'Unknown')}",
                "",
                "### Pronunciation Guide",
                production_notes.get("pronunciation", "No special pronunciations noted."),
                "",
                "### Music/Sound Suggestions",
                production_notes.get("music", ""),
                "",
                "---",
                "",
                "*Script generated with Montaigne*",
            ]
        )

    return "\n".join(lines)
