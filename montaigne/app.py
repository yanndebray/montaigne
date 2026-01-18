"""Streamlit web app for presentation slide editing and voiceover script management."""

import re
import tempfile
from pathlib import Path
from typing import Dict, List

import streamlit as st

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Montaigne - Presentation Editor",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


def extract_pdf_to_images(
    pdf_path: Path, output_dir: Path, progress_callback=None
) -> List[Path]:
    """Extract PDF pages to images using PyMuPDF."""
    import fitz

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    images = []
    total_pages = len(doc)

    zoom = 150 / 72  # 150 DPI
    matrix = fitz.Matrix(zoom, zoom)

    for page_num in range(total_pages):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=matrix)
        output_path = output_dir / f"page_{page_num + 1:03d}.png"
        pix.save(output_path)
        images.append(output_path)

        if progress_callback:
            progress_callback(page_num + 1, total_pages)

    doc.close()
    return images


def generate_thumbnail(image_path: Path, max_width: int = 200) -> bytes:
    """Generate a thumbnail for sidebar display."""
    from PIL import Image
    import io

    img = Image.open(image_path)
    ratio = max_width / img.width
    new_size = (max_width, int(img.height * ratio))
    img = img.resize(new_size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def parse_voiceover_script(script_content: str) -> List[Dict]:
    """Parse voiceover script markdown into structured data."""
    # Match headers like "## Slide 1: Title" or "## SLIDE 1 - Title"
    slides = re.split(r"##\s*[Ss]lide\s+(\d+)\s*[:\-\u2014\u2013]\s*", script_content)

    parsed_slides = []
    for i in range(1, len(slides), 2):
        if i + 1 >= len(slides):
            break

        slide_num = int(slides[i])
        slide_content = slides[i + 1]

        # Extract title (first line or from **"Title"**)
        title_match = re.search(r'\*\*"([^"]+)"\*\*', slide_content)
        if title_match:
            title = title_match.group(1)
        else:
            first_line = slide_content.strip().split("\n")[0]
            title = first_line.strip()[:50] if first_line else f"Slide {slide_num}"

        # Extract duration
        duration_match = re.search(r"\*\*Duration:\*\*\s*([^\n]+)", slide_content)
        duration = duration_match.group(1).strip() if duration_match else "30-45 seconds"

        # Extract tone
        tone_match = re.search(r"\*\*Tone:\*\*\s*([^\n]+)", slide_content)
        tone = tone_match.group(1).strip() if tone_match else "Professional"

        # Extract voice-over text (after "### Voice-Over:" or "Duration:")
        voiceover_text = ""
        lines = slide_content.split("\n")
        capture = False

        for line in lines:
            if "Voice-Over:" in line or "VOICE-OVER:" in line:
                capture = True
                continue
            if line.startswith("---") or line.startswith("## "):
                break
            if capture and line.strip():
                stripped = line.strip()
                if stripped and not stripped.startswith("**"):
                    voiceover_text += stripped + "\n"

        # Fallback: capture after Duration if no Voice-Over section
        if not voiceover_text.strip():
            capture = False
            for line in lines:
                if "Duration:" in line:
                    capture = True
                    continue
                if line.startswith("---") or line.startswith("## "):
                    break
                if capture and line.strip():
                    stripped = line.strip()
                    if stripped and not stripped.startswith("**") and not stripped.startswith("*"):
                        voiceover_text += stripped + "\n"

        parsed_slides.append(
            {
                "number": slide_num,
                "title": title,
                "duration": duration,
                "tone": tone,
                "text": voiceover_text.strip(),
            }
        )

    return parsed_slides


def format_script_markdown(slides_data: List[Dict], title: str = "Presentation") -> str:
    """Format slide data back to markdown script."""
    lines = [
        f"# {title}",
        "## Voice-Over Script",
        "",
        f"**Total slides:** {len(slides_data)}",
        "",
        "---",
        "",
    ]

    for slide in slides_data:
        lines.extend(
            [
                f"## Slide {slide['number']}: {slide['title']}",
                f"**Duration:** {slide['duration']}",
                f"**Tone:** {slide['tone']}",
                "",
                "### Voice-Over:",
                "",
                slide["text"],
                "",
                "---",
                "",
            ]
        )

    lines.append("*Script edited with Montaigne*")
    return "\n".join(lines)


def init_session_state():
    """Initialize session state variables."""
    if "slides" not in st.session_state:
        st.session_state.slides = []  # List of image paths
    if "scripts" not in st.session_state:
        st.session_state.scripts = []  # List of script dicts
    if "selected_slide" not in st.session_state:
        st.session_state.selected_slide = 0
    if "presentation_title" not in st.session_state:
        st.session_state.presentation_title = "Presentation"
    if "temp_dir" not in st.session_state:
        st.session_state.temp_dir = None
    if "modified" not in st.session_state:
        st.session_state.modified = False
    if "thumbnails" not in st.session_state:
        st.session_state.thumbnails = {}  # Cache: path -> thumbnail bytes
    if "loaded_pdf_name" not in st.session_state:
        st.session_state.loaded_pdf_name = None  # Track which PDF was loaded
    if "loaded_script_name" not in st.session_state:
        st.session_state.loaded_script_name = None  # Track which script was loaded
    if "editor_version" not in st.session_state:
        st.session_state.editor_version = 0  # Incremented to force widget refresh


def load_images_from_folder(folder_path: Path) -> List[Path]:
    """Load images from a folder."""
    extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    images = sorted([f for f in folder_path.iterdir() if f.suffix.lower() in extensions])
    return images


def get_cached_thumbnail(image_path: Path, max_width: int = 180) -> bytes:
    """Get thumbnail from cache or generate and cache it."""
    cache_key = str(image_path)
    if cache_key not in st.session_state.thumbnails:
        st.session_state.thumbnails[cache_key] = generate_thumbnail(image_path, max_width)
    return st.session_state.thumbnails[cache_key]


def generate_thumbnails_for_slides(slides: List[Path]) -> None:
    """Pre-generate thumbnails for all slides with progress indicator."""
    progress_bar = st.progress(0, text="Generating thumbnails...")
    for i, slide_path in enumerate(slides):
        get_cached_thumbnail(slide_path)
        progress_bar.progress((i + 1) / len(slides), text=f"Generating thumbnail {i + 1}/{len(slides)}")
    progress_bar.empty()


def render_sidebar():
    """Render the sidebar with slide thumbnails."""
    with st.sidebar:
        st.title("📑 Slides")

        # File upload section
        with st.expander("📂 Load Presentation", expanded=not st.session_state.slides):
            # PDF upload
            pdf_file = st.file_uploader("Upload PDF", type=["pdf"], key="pdf_uploader")
            if pdf_file and pdf_file.name != st.session_state.loaded_pdf_name:
                # Create temp directory
                if st.session_state.temp_dir is None:
                    st.session_state.temp_dir = tempfile.mkdtemp()

                temp_dir = Path(st.session_state.temp_dir)
                pdf_path = temp_dir / pdf_file.name
                images_dir = temp_dir / "slides"

                # Save uploaded PDF
                with open(pdf_path, "wb") as f:
                    f.write(pdf_file.getbuffer())

                # Extract with progress bar
                progress_bar = st.progress(0, text="Extracting slides...")

                def update_progress(current, total):
                    progress_bar.progress(current / total, text=f"Extracting slide {current}/{total}")

                images = extract_pdf_to_images(pdf_path, images_dir, update_progress)
                progress_bar.empty()

                st.session_state.slides = images
                st.session_state.presentation_title = pdf_path.stem
                st.session_state.thumbnails = {}  # Clear old thumbnails
                st.session_state.loaded_pdf_name = pdf_file.name  # Mark as loaded

                # Generate thumbnails with progress
                generate_thumbnails_for_slides(images)

                # Initialize empty scripts for each slide
                st.session_state.scripts = [
                    {
                        "number": i + 1,
                        "title": f"Slide {i + 1}",
                        "duration": "30-45 seconds",
                        "tone": "Professional",
                        "text": "",
                    }
                    for i in range(len(images))
                ]
                st.session_state.selected_slide = 0
                st.success(f"Loaded {len(images)} slides!")
                st.rerun()

            # Script upload
            script_file = st.file_uploader(
                "Upload Voiceover Script (.md)", type=["md", "txt"], key="script_uploader"
            )
            if script_file and st.session_state.slides:
                if script_file.name != st.session_state.loaded_script_name:
                    content = script_file.read().decode("utf-8")
                    parsed = parse_voiceover_script(content)

                    # Map parsed scripts to slides
                    for script in parsed:
                        idx = script["number"] - 1
                        if 0 <= idx < len(st.session_state.scripts):
                            st.session_state.scripts[idx] = script

                    st.session_state.loaded_script_name = script_file.name
                    st.session_state.script_load_count = len(parsed)
                    # Increment version to force new widget keys
                    st.session_state.editor_version += 1
                    st.rerun()

            # Show success message after rerun
            if st.session_state.get("script_load_count"):
                st.success(f"Loaded scripts for {st.session_state.script_load_count} slides!")
                st.session_state.script_load_count = None

            # Folder path input with better UX
            st.markdown("**Or load from folder:**")
            folder_path = st.text_input(
                "Image folder path:",
                placeholder="C:/path/to/slides or /path/to/slides",
                help="Enter the full path to a folder containing slide images (PNG, JPG, etc.)",
                label_visibility="collapsed",
            )
            if folder_path and st.button("📁 Load from Folder", type="secondary"):
                path = Path(folder_path)
                if path.exists() and path.is_dir():
                    images = load_images_from_folder(path)
                    if images:
                        st.session_state.slides = images
                        st.session_state.presentation_title = path.name
                        st.session_state.thumbnails = {}  # Clear old thumbnails

                        # Generate thumbnails with progress
                        generate_thumbnails_for_slides(images)

                        st.session_state.scripts = [
                            {
                                "number": i + 1,
                                "title": f"Slide {i + 1}",
                                "duration": "30-45 seconds",
                                "tone": "Professional",
                                "text": "",
                            }
                            for i in range(len(images))
                        ]
                        st.session_state.selected_slide = 0
                        st.success(f"Loaded {len(images)} slides!")
                        st.rerun()
                    else:
                        st.error("No images found in folder")
                else:
                    st.error("Folder not found")

        # Slide thumbnails in scrollable container
        if st.session_state.slides:
            st.divider()
            st.subheader(f"📊 {len(st.session_state.slides)} Slides")

            # Create scrollable container for slides
            with st.container(height=500):
                for i, slide_path in enumerate(st.session_state.slides):
                    is_selected = i == st.session_state.selected_slide

                    # Slide header with number and title
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        badge_style = (
                            "background-color: #ff4b4b; color: white;"
                            if is_selected
                            else "background-color: #444; color: white;"
                        )
                        st.markdown(
                            f'<span style="padding: 4px 8px; border-radius: 4px; {badge_style}">'
                            f"{i + 1}</span>",
                            unsafe_allow_html=True,
                        )
                    with col2:
                        title = "Untitled"
                        if i < len(st.session_state.scripts):
                            title = st.session_state.scripts[i].get("title", f"Slide {i + 1}")
                        st.caption(title[:20] + "..." if len(title) > 20 else title)

                    # Thumbnail (cached for performance)
                    try:
                        thumb = get_cached_thumbnail(slide_path, max_width=180)
                        st.image(thumb, width="stretch")
                    except Exception:
                        st.image(str(slide_path), width="stretch")

                    # Select button
                    if st.button(
                        "Select" if not is_selected else "Selected",
                        key=f"slide_btn_{i}",
                        type="primary" if is_selected else "secondary",
                    ):
                        st.session_state.selected_slide = i
                        st.rerun()

                    st.divider()


def render_main_panel():
    """Render the main editing panel."""
    if not st.session_state.slides:
        st.title("🎬 Montaigne")
        st.subheader("Presentation Editor")
        st.write("Upload a PDF or select an image folder to get started.")

        st.markdown(
            """
        ### Features
        - 📑 **Slide Navigation**: Browse slides like in PowerPoint
        - ✏️ **Script Editor**: Edit voiceover scripts for each slide
        - 💾 **Export**: Save edited scripts as markdown
        - 🎨 **Visual Editing**: See your slides while editing

        ### Getting Started
        1. Upload a PDF in the sidebar
        2. Optionally upload an existing voiceover script
        3. Click on slides to select them
        4. Edit the script in the main panel
        5. Export when done
        """
        )
        return

    # Header with navigation
    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        if st.button("⬅️ Previous", disabled=st.session_state.selected_slide == 0):
            st.session_state.selected_slide -= 1
            st.rerun()

    with col2:
        total = len(st.session_state.slides)
        current = st.session_state.selected_slide + 1
        st.markdown(
            f"<h2 style='text-align: center;'>Slide {current} of {total}</h2>",
            unsafe_allow_html=True,
        )

    with col3:
        max_idx = len(st.session_state.slides) - 1
        if st.button("Next ➡️", disabled=st.session_state.selected_slide == max_idx):
            st.session_state.selected_slide += 1
            st.rerun()

    st.divider()

    # Main content area - two columns
    slide_col, editor_col = st.columns([1, 1])

    idx = st.session_state.selected_slide
    slide_path = st.session_state.slides[idx]
    script = st.session_state.scripts[idx] if idx < len(st.session_state.scripts) else {}

    with slide_col:
        st.subheader("🖼️ Slide Preview")
        st.image(str(slide_path), width="stretch")

        # Slide info
        with st.expander("📋 Slide Info"):
            st.text(f"File: {slide_path.name}")
            if slide_path.exists():
                size_mb = slide_path.stat().st_size / (1024 * 1024)
                st.text(f"Size: {size_mb:.2f} MB")

    with editor_col:
        st.subheader("✏️ Script Editor")

        # Version suffix ensures widgets refresh when scripts are loaded
        v = st.session_state.editor_version

        # Title
        new_title = st.text_input(
            "Title", value=script.get("title", f"Slide {idx + 1}"), key=f"title_{idx}_v{v}"
        )

        # Duration and Tone in columns
        dur_col, tone_col = st.columns(2)

        with dur_col:
            new_duration = st.text_input(
                "Duration", value=script.get("duration", "30-45 seconds"), key=f"duration_{idx}_v{v}"
            )

        with tone_col:
            new_tone = st.text_input(
                "Tone", value=script.get("tone", "Professional"), key=f"tone_{idx}_v{v}"
            )

        # Voice-over text
        new_text = st.text_area(
            "Voice-Over Script",
            value=script.get("text", ""),
            height=300,
            key=f"text_{idx}_v{v}",
            placeholder="Enter the voiceover script for this slide...",
        )

        # Update script data
        if idx < len(st.session_state.scripts):
            current = st.session_state.scripts[idx]
            if (
                new_title != current.get("title")
                or new_duration != current.get("duration")
                or new_tone != current.get("tone")
                or new_text != current.get("text")
            ):

                st.session_state.scripts[idx] = {
                    "number": idx + 1,
                    "title": new_title,
                    "duration": new_duration,
                    "tone": new_tone,
                    "text": new_text,
                }
                st.session_state.modified = True

        # Word count
        word_count = len(new_text.split()) if new_text else 0
        est_duration = word_count / 140  # ~140 words per minute
        st.caption(f"📝 {word_count} words • ⏱️ ~{est_duration:.1f} min reading time")

    # Export section
    st.divider()
    export_col1, export_col2, export_col3 = st.columns([1, 1, 1])

    with export_col1:
        if st.session_state.modified:
            st.warning("⚠️ You have unsaved changes")

    with export_col2:
        # Export as markdown
        markdown = format_script_markdown(
            st.session_state.scripts, st.session_state.presentation_title
        )
        st.download_button(
            label="💾 Export Script",
            data=markdown,
            file_name=f"{st.session_state.presentation_title}_voiceover.md",
            mime="text/markdown",
            type="primary",
        )

    with export_col3:
        # Quick stats
        total_words = sum(len(s.get("text", "").split()) for s in st.session_state.scripts)
        st.metric("Total Words", f"{total_words:,}")


def main():
    """Main app entry point."""
    init_session_state()
    render_sidebar()
    render_main_panel()


if __name__ == "__main__":
    main()
