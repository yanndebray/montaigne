"""
Web-based Video Annotation Server.

Features:
- Frame-accurate video player with waveform visualization
- Auto-pause on typing (Frictionless Capture pattern)
- Keyboard shortcuts for power users (I/O for in/out, brackets for nudging)
- Local SQLite storage with zero-latency persistence
- No-login review (guest user support)
- Export to WebVTT/SRT formats
"""

import mimetypes
import tempfile
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_file, Response
from werkzeug.utils import secure_filename

from .annotation import (
    Annotation,
    AnnotationStore,
    AnnotationCategory,
    AnnotationStatus,
    export_to_webvtt,
    export_to_srt,
    export_to_json,
    get_media_id,
)
from .logging import get_logger

logger = get_logger(__name__)


def create_app(
    media_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> Flask:
    """Create and configure the annotation server Flask app."""
    app = Flask(__name__)
    app.config["MEDIA_PATH"] = media_path
    app.config["STORE"] = AnnotationStore(db_path)

    # ==========================================================================
    # Static Assets
    # ==========================================================================

    @app.route("/")
    def index():
        """Serve the main annotation interface."""
        return get_html_template()

    @app.route("/media")
    def serve_media():
        """Serve the media file with range request support for seeking."""
        media = app.config["MEDIA_PATH"]
        if not media or not media.exists():
            return jsonify({"error": "No media file configured"}), 404

        # Support range requests for video seeking
        range_header = request.headers.get("Range")
        file_size = media.stat().st_size
        mime_type = mimetypes.guess_type(str(media))[0] or "application/octet-stream"

        if range_header:
            # Parse range header
            byte_range = range_header.replace("bytes=", "").split("-")
            start = int(byte_range[0])
            end = int(byte_range[1]) if byte_range[1] else file_size - 1

            if start >= file_size:
                return Response(status=416)  # Range not satisfiable

            length = end - start + 1

            with open(media, "rb") as f:
                f.seek(start)
                data = f.read(length)

            response = Response(
                data,
                status=206,
                mimetype=mime_type,
                direct_passthrough=True,
            )
            response.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            response.headers["Accept-Ranges"] = "bytes"
            response.headers["Content-Length"] = length
            return response

        return send_file(media, mimetype=mime_type)

    @app.route("/media/info")
    def media_info():
        """Get media file information."""
        media = app.config["MEDIA_PATH"]
        if not media or not media.exists():
            return jsonify({"error": "No media file configured"}), 404

        return jsonify(
            {
                "filename": media.name,
                "path": str(media),
                "size": media.stat().st_size,
                "media_id": get_media_id(media),
                "mime_type": mimetypes.guess_type(str(media))[0],
            }
        )

    @app.route("/api/status")
    def get_status():
        """Get current app status including whether media is loaded."""
        media = app.config["MEDIA_PATH"]
        has_media = media is not None and media.exists()
        return jsonify(
            {
                "has_media": has_media,
                "filename": media.name if has_media else None,
                "mime_type": mimetypes.guess_type(str(media))[0] if has_media else None,
            }
        )

    @app.route("/api/upload", methods=["POST"])
    def upload_media():
        """Upload a media file for annotation."""
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Validate file type
        allowed_extensions = {
            ".mp4",
            ".webm",
            ".mov",
            ".avi",
            ".mkv",
            ".m4v",
            ".mp3",
            ".wav",
            ".m4a",
            ".aac",
            ".ogg",
            ".flac",
        }
        filename = secure_filename(file.filename)
        ext = Path(filename).suffix.lower()

        if ext not in allowed_extensions:
            return jsonify({"error": f"Unsupported file type: {ext}"}), 400

        # Save to temp directory
        temp_dir = Path(tempfile.gettempdir()) / "montaigne_annotate"
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / filename

        file.save(temp_path)
        app.config["MEDIA_PATH"] = temp_path

        logger.info("Uploaded media file: %s", temp_path)

        return jsonify(
            {
                "success": True,
                "filename": filename,
                "path": str(temp_path),
                "media_id": get_media_id(temp_path),
                "mime_type": mimetypes.guess_type(str(temp_path))[0],
            }
        )

    # ==========================================================================
    # Annotation API
    # ==========================================================================

    @app.route("/api/annotations", methods=["GET"])
    def list_annotations():
        """List all annotations for the current media."""
        media = app.config["MEDIA_PATH"]
        if not media:
            return jsonify({"annotations": []})

        media_id = get_media_id(media)
        store: AnnotationStore = app.config["STORE"]

        # Optional filters
        status = request.args.get("status")
        category = request.args.get("category")

        annotations = store.get_by_media(
            media_id,
            status=AnnotationStatus(status) if status else None,
            category=AnnotationCategory(category) if category else None,
        )

        return jsonify(
            {
                "media_id": media_id,
                "count": len(annotations),
                "annotations": [ann.to_dict() for ann in annotations],
            }
        )

    @app.route("/api/annotations", methods=["POST"])
    def create_annotation():
        """Create a new annotation."""
        media = app.config["MEDIA_PATH"]
        if not media:
            return jsonify({"error": "No media file configured"}), 400

        data = request.json
        media_id = get_media_id(media)
        store: AnnotationStore = app.config["STORE"]

        annotation = Annotation.create(
            media_id=media_id,
            start_ms=data["start_ms"],
            text=data["text"],
            end_ms=data.get("end_ms"),
            category=AnnotationCategory(data.get("category", "general")),
            author=data.get("author", "anonymous"),
            shape=data.get("shape"),
            parent_id=data.get("parent_id"),
        )

        store.save(annotation)
        logger.info("Created annotation: %s at %dms", annotation.id[:8], annotation.start_ms)

        return jsonify(annotation.to_dict()), 201

    @app.route("/api/annotations/<annotation_id>", methods=["GET"])
    def get_annotation(annotation_id: str):
        """Get a specific annotation."""
        store: AnnotationStore = app.config["STORE"]
        annotation = store.get(annotation_id)

        if not annotation:
            return jsonify({"error": "Annotation not found"}), 404

        return jsonify(annotation.to_dict())

    @app.route("/api/annotations/<annotation_id>", methods=["PUT"])
    def update_annotation(annotation_id: str):
        """Update an existing annotation."""
        store: AnnotationStore = app.config["STORE"]
        annotation = store.get(annotation_id)

        if not annotation:
            return jsonify({"error": "Annotation not found"}), 404

        data = request.json

        # Update allowed fields
        if "text" in data:
            annotation.text = data["text"]
        if "start_ms" in data:
            annotation.start_ms = data["start_ms"]
        if "end_ms" in data:
            annotation.end_ms = data["end_ms"]
        if "category" in data:
            annotation.category = AnnotationCategory(data["category"])
        if "status" in data:
            annotation.status = AnnotationStatus(data["status"])
        if "shape" in data:
            annotation.shape = data["shape"]

        store.save(annotation)
        logger.info("Updated annotation: %s", annotation_id[:8])

        return jsonify(annotation.to_dict())

    @app.route("/api/annotations/<annotation_id>", methods=["DELETE"])
    def delete_annotation(annotation_id: str):
        """Delete an annotation."""
        store: AnnotationStore = app.config["STORE"]

        if store.delete(annotation_id):
            logger.info("Deleted annotation: %s", annotation_id[:8])
            return jsonify({"success": True})

        return jsonify({"error": "Annotation not found"}), 404

    @app.route("/api/annotations/at/<int:time_ms>", methods=["GET"])
    def get_annotations_at_time(time_ms: int):
        """Get annotations visible at a specific time (optimized for playback)."""
        media = app.config["MEDIA_PATH"]
        if not media:
            return jsonify({"annotations": []})

        media_id = get_media_id(media)
        store: AnnotationStore = app.config["STORE"]

        annotations = store.get_at_time(media_id, time_ms)

        return jsonify(
            {
                "time_ms": time_ms,
                "annotations": [ann.to_dict() for ann in annotations],
            }
        )

    # ==========================================================================
    # Export Endpoints
    # ==========================================================================

    @app.route("/api/export/<format>")
    def export_annotations(format: str):
        """Export annotations to various formats."""
        media = app.config["MEDIA_PATH"]
        if not media:
            return jsonify({"error": "No media file configured"}), 400

        media_id = get_media_id(media)
        store: AnnotationStore = app.config["STORE"]
        annotations = store.get_by_media(media_id)

        if not annotations:
            return jsonify({"error": "No annotations to export"}), 404

        # Create export file
        export_dir = Path("/tmp/montaigne_exports")
        export_dir.mkdir(parents=True, exist_ok=True)

        include_metadata = request.args.get("metadata", "true").lower() == "true"

        if format == "vtt":
            output_path = export_dir / f"{media.stem}_annotations.vtt"
            export_to_webvtt(annotations, output_path, include_metadata)
            return send_file(output_path, mimetype="text/vtt", as_attachment=True)

        elif format == "srt":
            output_path = export_dir / f"{media.stem}_annotations.srt"
            export_to_srt(annotations, output_path, include_metadata)
            return send_file(output_path, mimetype="text/plain", as_attachment=True)

        elif format == "json":
            output_path = export_dir / f"{media.stem}_annotations.json"
            export_to_json(annotations, output_path)
            return send_file(output_path, mimetype="application/json", as_attachment=True)

        else:
            return jsonify({"error": f"Unknown format: {format}"}), 400

    return app


def get_html_template() -> str:
    """Return the main HTML template for the annotation interface."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>montaigne - annotate</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>✒️</text></svg>">

    <!-- Video.js -->
    <link href="https://cdn.jsdelivr.net/npm/video.js@8/dist/video-js.min.css" rel="stylesheet">

    <!-- WaveSurfer.js for waveform -->
    <script src="https://cdn.jsdelivr.net/npm/wavesurfer.js@7/dist/wavesurfer.min.js"></script>

    <!-- Crimson Pro font for logo -->
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@500&display=swap" rel="stylesheet">

    <style>
        /* Dark theme (default) */
        :root {
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-tertiary: #0f0f23;
            --text-primary: #eaeaea;
            --text-secondary: #a0a0a0;
            --accent: #e94560;
            --accent-hover: #ff6b6b;
            --success: #4ecca3;
            --warning: #ffc93c;
            --border: #2a2a4a;
            --video-bg: #000000;
            --logo-text: #1a1816;
            --header-bg: var(--bg-secondary);
        }

        /* Light theme (Streamlit-inspired) */
        [data-theme="light"] {
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-tertiary: #f0f2f6;
            --text-primary: #262730;
            --text-secondary: #6b7280;
            --accent: #ff4b4b;
            --accent-hover: #ff6b6b;
            --success: #21c354;
            --warning: #faca2b;
            --border: #e6e9ef;
            --video-bg: #0e1117;
            --logo-text: #1a1816;
            --header-bg: #ffffff;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 20px;
            background: var(--header-bg);
            border-bottom: 1px solid var(--border);
            transition: background-color 0.3s ease;
        }

        /* Montaigne logo styling (Crimson Pro, Streamlit-inspired) */
        .montaigne-logo {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            text-decoration: none;
        }

        .montaigne-logo .logo-icon {
            font-size: 1.5rem;
            line-height: 1;
        }

        .montaigne-logo .logo-text {
            font-family: 'Crimson Pro', Georgia, serif;
            font-size: 1.4rem;
            font-weight: 500;
            letter-spacing: -0.02em;
            color: var(--text-primary);
        }

        .montaigne-logo .logo-suffix {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.85rem;
            font-weight: 400;
            color: var(--text-secondary);
            margin-left: 4px;
        }

        /* Theme toggle button */
        .theme-toggle {
            width: 40px;
            height: 40px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            transition: all 0.2s;
        }

        .theme-toggle:hover {
            background: var(--border);
        }

        [data-theme="light"] .theme-toggle .icon-sun {
            display: none;
        }

        [data-theme="light"] .theme-toggle .icon-moon {
            display: block;
        }

        .theme-toggle .icon-moon {
            display: none;
        }

        .theme-toggle .icon-sun {
            display: block;
        }

        /* Help button */
        .help-btn {
            width: 40px;
            height: 40px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            font-weight: 600;
            transition: all 0.2s;
            position: relative;
        }

        .help-btn:hover {
            background: var(--border);
        }

        .help-dropdown {
            position: absolute;
            top: 100%;
            right: 0;
            margin-top: 8px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 16px;
            min-width: 220px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            display: none;
            z-index: 100;
        }

        .help-dropdown.show {
            display: block;
        }

        [data-theme="light"] .help-dropdown {
            background: var(--bg-primary);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .help-dropdown h4 {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .help-shortcut {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            font-size: 0.85rem;
        }

        .help-shortcut kbd {
            background: var(--bg-tertiary);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', monospace;
            font-size: 0.75rem;
        }

        [data-theme="light"] .help-shortcut kbd {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
        }

        .toolbar {
            display: flex;
            gap: 10px;
        }

        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s;
        }

        .btn-primary {
            background: var(--accent);
            color: white;
        }

        .btn-primary:hover {
            background: var(--accent-hover);
        }

        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border);
            transition: background-color 0.2s, border-color 0.2s, color 0.2s;
        }

        .btn-secondary:hover {
            background: var(--border);
        }

        /* Light theme specific button adjustments */
        [data-theme="light"] .btn-secondary {
            background: var(--bg-secondary);
            border-color: var(--border);
        }

        [data-theme="light"] .btn-secondary:hover {
            background: var(--bg-tertiary);
        }

        /* Export dropdown */
        .export-dropdown {
            position: relative;
        }

        .export-main {
            display: flex;
            align-items: center;
            gap: 8px;
            height: 40px;
            padding: 0 12px;
        }

        .dropdown-arrow {
            padding: 0 4px;
            margin-left: 4px;
            border-left: 1px solid rgba(255, 255, 255, 0.3);
            cursor: pointer;
        }

        .dropdown-arrow:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .export-menu {
            position: absolute;
            top: 100%;
            right: 0;
            margin-top: 4px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            min-width: 150px;
            display: none;
            z-index: 100;
            overflow: hidden;
        }

        .export-menu.show {
            display: block;
        }

        .export-menu button {
            display: block;
            width: 100%;
            padding: 10px 16px;
            border: none;
            background: none;
            color: var(--text-primary);
            text-align: left;
            cursor: pointer;
            font-size: 0.9rem;
            transition: background-color 0.2s;
        }

        .export-menu button:hover {
            background: var(--bg-tertiary);
        }

        [data-theme="light"] .export-menu {
            background: var(--bg-primary);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        [data-theme="light"] .export-menu button:hover {
            background: var(--bg-secondary);
        }

        .main-content {
            display: grid;
            grid-template-columns: 1fr 350px;
            gap: 20px;
            margin-top: 20px;
        }

        /* Upload Dropzone */
        .upload-dropzone {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 60px 40px;
            text-align: center;
            border: 2px dashed var(--border);
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .upload-dropzone:hover,
        .upload-dropzone.dragover {
            border-color: var(--accent);
            background: rgba(233, 69, 96, 0.05);
        }

        [data-theme="light"] .upload-dropzone:hover,
        [data-theme="light"] .upload-dropzone.dragover {
            background: rgba(255, 75, 75, 0.05);
        }

        .upload-dropzone .upload-icon {
            font-size: 4rem;
            margin-bottom: 20px;
            opacity: 0.6;
        }

        .upload-dropzone h2 {
            font-size: 1.5rem;
            margin-bottom: 10px;
            color: var(--text-primary);
        }

        .upload-dropzone p {
            color: var(--text-secondary);
            margin-bottom: 20px;
        }

        .upload-dropzone .supported-formats {
            font-size: 0.85rem;
            color: var(--text-secondary);
            opacity: 0.7;
        }

        .upload-dropzone input[type="file"] {
            display: none;
        }

        .upload-dropzone.hidden {
            display: none;
        }

        .upload-dropzone .upload-btn {
            display: inline-block;
            padding: 12px 24px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        .upload-dropzone .upload-btn:hover {
            background: var(--accent-hover);
        }

        .upload-progress {
            margin-top: 20px;
            display: none;
        }

        .upload-progress.active {
            display: block;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-bar-fill {
            height: 100%;
            background: var(--accent);
            width: 0%;
            transition: width 0.3s ease;
        }

        .upload-status {
            margin-top: 10px;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        /* Video Player */
        .player-section {
            background: var(--bg-secondary);
            border-radius: 12px;
            overflow: hidden;
            transition: background-color 0.3s ease;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .player-section.hidden {
            display: none;
        }

        [data-theme="light"] .player-section {
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 0 0 1px var(--border);
        }

        .video-container {
            position: relative;
            background: var(--video-bg);
        }

        #video-player {
            width: 100%;
            height: auto;
            max-height: 60vh;
        }

        .video-js {
            width: 100%;
            height: auto;
            aspect-ratio: 16/9;
        }

        /* Waveform */
        .waveform-container {
            position: relative;
            background: var(--bg-tertiary);
            padding: 10px;
            border-top: 1px solid var(--border);
            transition: background-color 0.3s ease;
        }

        [data-theme="light"] .waveform-container {
            background: var(--bg-secondary);
        }

        #waveform {
            width: 100%;
            height: 80px;
        }

        .waveform-markers {
            position: absolute;
            top: 0;
            left: 10px;
            right: 10px;
            height: 100%;
            pointer-events: none;
        }

        .annotation-marker {
            position: absolute;
            top: 10px;
            bottom: 10px;
            background: rgba(233, 69, 96, 0.3);
            border-left: 2px solid var(--accent);
            cursor: pointer;
            pointer-events: auto;
        }

        .annotation-marker.point {
            width: 4px;
            background: var(--accent);
        }

        /* Controls */
        .controls-bar {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
            transition: background-color 0.3s ease;
        }

        .time-display {
            font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
            font-size: 1.1rem;
            color: var(--text-secondary);
            min-width: 180px;
        }

        .time-display .current {
            color: var(--text-primary);
        }

        .playback-controls {
            display: flex;
            gap: 8px;
        }

        .playback-controls button {
            width: 40px;
            height: 40px;
            border: none;
            border-radius: 50%;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            cursor: pointer;
            font-size: 1.2rem;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }

        [data-theme="light"] .playback-controls button {
            background: var(--bg-primary);
            border: 1px solid var(--border);
        }

        .playback-controls button:hover {
            background: var(--border);
        }

        [data-theme="light"] .playback-controls button:hover {
            background: var(--bg-tertiary);
        }

        .playback-controls button.active {
            background: var(--accent);
        }

        .range-controls {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-left: auto;
        }

        .range-display {
            font-family: 'SF Mono', monospace;
            font-size: 0.85rem;
            padding: 4px 8px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            transition: background-color 0.3s ease;
        }

        [data-theme="light"] .range-display {
            background: var(--bg-primary);
            border: 1px solid var(--border);
        }

        .range-display.active {
            background: rgba(233, 69, 96, 0.2);
            color: var(--accent);
        }

        [data-theme="light"] .range-display.active {
            background: rgba(255, 75, 75, 0.15);
        }

        /* Annotation Panel */
        .annotation-panel {
            background: var(--bg-secondary);
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            max-height: calc(100vh - 120px);
            transition: background-color 0.3s ease;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        [data-theme="light"] .annotation-panel {
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 0 0 1px var(--border);
        }

        .panel-header {
            padding: 15px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .panel-header h2 {
            font-size: 1.1rem;
            font-weight: 600;
        }

        .annotation-count {
            font-size: 0.85rem;
            color: var(--text-secondary);
            background: var(--bg-tertiary);
            padding: 2px 8px;
            border-radius: 10px;
        }

        /* Input Area */
        .input-area {
            padding: 15px;
            border-bottom: 1px solid var(--border);
        }

        .input-timestamp {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            font-size: 0.85rem;
        }

        .input-timestamp span {
            color: var(--text-secondary);
        }

        .input-timestamp .time {
            font-family: 'SF Mono', monospace;
            color: var(--accent);
        }

        #annotation-input {
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 0.95rem;
            resize: none;
            min-height: 80px;
            transition: background-color 0.3s ease, border-color 0.2s ease;
        }

        [data-theme="light"] #annotation-input {
            background: var(--bg-primary);
        }

        #annotation-input:focus {
            outline: none;
            border-color: var(--accent);
        }

        #annotation-input::placeholder {
            color: var(--text-secondary);
        }

        .input-actions {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }

        .category-select {
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 0.85rem;
            flex: 1;
            transition: background-color 0.3s ease;
        }

        [data-theme="light"] .category-select {
            background: var(--bg-primary);
        }

        /* Annotation List */
        .annotation-list {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }

        .annotation-item {
            padding: 12px;
            background: var(--bg-tertiary);
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s, background-color 0.3s ease;
            border-left: 3px solid transparent;
        }

        [data-theme="light"] .annotation-item {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-left: 3px solid transparent;
        }

        .annotation-item:hover {
            background: var(--border);
        }

        .annotation-item.active {
            border-left-color: var(--accent);
            background: rgba(233, 69, 96, 0.1);
        }

        .annotation-item.resolved {
            opacity: 0.6;
        }

        .annotation-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }

        .annotation-time {
            font-family: 'SF Mono', monospace;
            font-size: 0.8rem;
            color: var(--accent);
        }

        .annotation-category {
            font-size: 0.7rem;
            padding: 2px 6px;
            border-radius: 4px;
            background: var(--bg-secondary);
            color: var(--text-secondary);
            text-transform: uppercase;
        }

        .annotation-text {
            font-size: 0.9rem;
            line-height: 1.4;
        }

        .annotation-meta {
            display: flex;
            gap: 10px;
            margin-top: 8px;
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .annotation-actions {
            display: flex;
            gap: 6px;
            margin-top: 8px;
        }

        .annotation-actions button {
            padding: 4px 8px;
            font-size: 0.75rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            background: var(--bg-secondary);
            color: var(--text-secondary);
        }

        .annotation-actions button:hover {
            background: var(--border);
            color: var(--text-primary);
        }

        .annotation-actions button.resolve {
            color: var(--success);
        }

        .annotation-actions button.delete {
            color: var(--accent);
        }


        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-secondary);
        }

        .empty-state svg {
            width: 64px;
            height: 64px;
            margin-bottom: 15px;
            opacity: 0.5;
        }

        /* Toast notifications */
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 20px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            animation: slideIn 0.3s ease;
            z-index: 1000;
            transition: background-color 0.3s ease;
        }

        [data-theme="light"] .toast {
            background: var(--bg-primary);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        .toast.success {
            border-color: var(--success);
        }

        .toast.error {
            border-color: var(--accent);
        }

        /* Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            animation: fadeIn 0.2s ease;
        }

        .modal {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 0;
            min-width: 320px;
            max-width: 90%;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            animation: scaleIn 0.2s ease;
        }

        [data-theme="light"] .modal {
            background: var(--bg-primary);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
        }

        .modal-header {
            padding: 16px 20px;
            font-weight: 600;
            font-size: 1.1rem;
            border-bottom: 1px solid var(--border);
            color: var(--accent);
        }

        .modal-body {
            padding: 20px;
            color: var(--text-primary);
            line-height: 1.5;
        }

        .modal-footer {
            padding: 12px 20px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: flex-end;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes scaleIn {
            from { transform: scale(0.95); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }

        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        /* Mobile responsiveness */
        @media (max-width: 900px) {
            .main-content {
                grid-template-columns: 1fr;
            }

            .annotation-panel {
                max-height: 50vh;
            }
        }
    </style>
</head>
<body>
    <header>
        <div class="montaigne-logo">
            <span class="logo-icon">✒️</span>
            <span class="logo-text">montaigne</span>
            <span class="logo-suffix">annotate</span>
        </div>
        <div class="toolbar">
            <button class="help-btn" onclick="toggleHelp()" title="Keyboard shortcuts">
                ?
                <div class="help-dropdown" id="help-dropdown">
                    <h4>Keyboard Shortcuts</h4>
                    <div class="help-shortcut"><span>Play/Pause</span><kbd>Space</kbd></div>
                    <div class="help-shortcut"><span>Frame step</span><kbd>[</kbd> <kbd>]</kbd></div>
                    <div class="help-shortcut"><span>In/Out points</span><kbd>I</kbd> <kbd>O</kbd></div>
                    <div class="help-shortcut"><span>Submit</span><kbd>Ctrl+Enter</kbd></div>
                    <div class="help-shortcut"><span>Clear range</span><kbd>Esc</kbd></div>
                </div>
            </button>
            <button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme">
                <span class="icon-sun">&#9728;</span>
                <span class="icon-moon">&#9790;</span>
            </button>
            <div class="export-dropdown">
                <button class="btn btn-primary export-main" onclick="exportAnnotations('vtt')">
                    Export
                    <span class="dropdown-arrow" onclick="event.stopPropagation(); toggleExportMenu()">&#9662;</span>
                </button>
                <div class="export-menu" id="export-menu">
                    <button onclick="exportAnnotations('vtt'); closeExportMenu()">WebVTT (.vtt)</button>
                    <button onclick="exportAnnotations('srt'); closeExportMenu()">SubRip (.srt)</button>
                    <button onclick="exportAnnotations('json'); closeExportMenu()">JSON (.json)</button>
                </div>
            </div>
        </div>
    </header>

    <div class="container">
        <div class="main-content">
            <!-- Upload Dropzone (shown when no media is loaded) -->
            <div class="upload-dropzone" id="upload-dropzone">
                <div class="upload-icon">&#128249;</div>
                <h2>Drop your video or audio file here</h2>
                <p>or click to browse</p>
                <button class="upload-btn" onclick="document.getElementById('file-input').click()">
                    Choose File
                </button>
                <input type="file" id="file-input" accept="video/*,audio/*" onchange="handleFileSelect(event)">
                <div class="upload-progress" id="upload-progress">
                    <div class="progress-bar">
                        <div class="progress-bar-fill" id="progress-bar-fill"></div>
                    </div>
                    <div class="upload-status" id="upload-status">Uploading...</div>
                </div>
                <p class="supported-formats">
                    Supported: MP4, WebM, MOV, AVI, MKV, MP3, WAV, M4A, AAC, OGG, FLAC
                </p>
            </div>

            <div class="player-section hidden" id="player-section">
                <div class="video-container">
                    <video id="video-player" class="video-js" controls preload="auto">
                        <source src="/media" type="video/mp4" id="video-source">
                    </video>
                </div>

                <div class="waveform-container">
                    <div id="waveform"></div>
                    <div class="waveform-markers" id="waveform-markers"></div>
                </div>

                <div class="controls-bar">
                    <div class="time-display">
                        <span class="current" id="current-time">00:00:00.000</span>
                        <span> / </span>
                        <span id="duration">00:00:00.000</span>
                    </div>

                    <div class="playback-controls">
                        <button onclick="stepFrame(-1)" title="Previous frame ([)">&#9664;&#9664;</button>
                        <button onclick="togglePlay()" id="play-btn" title="Play/Pause (Space)">&#9654;</button>
                        <button onclick="stepFrame(1)" title="Next frame (])">&#9654;&#9654;</button>
                    </div>

                    <div class="range-controls">
                        <button class="btn btn-secondary" onclick="setInPoint()" title="Set In point (I)">I</button>
                        <span class="range-display" id="in-point">--:--</span>
                        <span>-</span>
                        <span class="range-display" id="out-point">--:--</span>
                        <button class="btn btn-secondary" onclick="setOutPoint()" title="Set Out point (O)">O</button>
                        <button class="btn btn-secondary" onclick="clearRange()" title="Clear range (Esc)">Clear</button>
                    </div>
                </div>
            </div>

            <div class="annotation-panel">
                <div class="panel-header">
                    <h2>Annotations</h2>
                    <span class="annotation-count" id="annotation-count">0</span>
                </div>

                <div class="input-area">
                    <div class="input-timestamp">
                        <span>Time:</span>
                        <span class="time" id="input-time">00:00:00.000</span>
                        <span id="range-indicator"></span>
                    </div>
                    <textarea
                        id="annotation-input"
                        placeholder="Start typing to add annotation... (auto-pauses video)"
                    ></textarea>
                    <div class="input-actions">
                        <select class="category-select" id="category-select">
                            <option value="general">General</option>
                            <option value="pacing">Pacing</option>
                            <option value="pronunciation">Pronunciation</option>
                            <option value="audio_quality">Audio Quality</option>
                            <option value="timing">Timing</option>
                            <option value="content">Content</option>
                            <option value="technical">Technical</option>
                        </select>
                        <button class="btn btn-primary" onclick="submitAnnotation()">Add (Ctrl+Enter)</button>
                    </div>
                </div>

                <div class="annotation-list" id="annotation-list">
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                        </svg>
                        <p>No annotations yet</p>
                        <p>Start typing while watching to add one</p>
                    </div>
                </div>

            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/video.js@8/dist/video.min.js"></script>
    <script>
        // ==========================================================================
        // State Management (Zustand-inspired pattern)
        // ==========================================================================
        const state = {
            currentTime: 0,
            duration: 0,
            isPlaying: false,
            inPoint: null,
            outPoint: null,
            annotations: [],
            activeAnnotation: null,
            fps: 30, // Default, updated from video metadata
        };

        // ==========================================================================
        // Video Player Setup
        // ==========================================================================
        let player = null;
        let wavesurfer = null;
        let videoElement = null;

        async function initPlayer() {
            // Initialize Video.js
            player = videojs('video-player', {
                controls: true,
                fluid: true,
                playbackRates: [0.5, 1, 1.5, 2],
            });

            videoElement = player.el().querySelector('video');

            // Wait for metadata
            player.on('loadedmetadata', () => {
                state.duration = player.duration() * 1000;
                updateTimeDisplay();
                initWaveform();
            });

            // Use requestVideoFrameCallback for frame-accurate time updates
            if ('requestVideoFrameCallback' in HTMLVideoElement.prototype) {
                function onFrame(now, metadata) {
                    state.currentTime = metadata.mediaTime * 1000;
                    updateTimeDisplay();
                    updateActiveAnnotations();
                    videoElement.requestVideoFrameCallback(onFrame);
                }
                videoElement.requestVideoFrameCallback(onFrame);
            } else {
                // Fallback for browsers without rVFC
                player.on('timeupdate', () => {
                    state.currentTime = player.currentTime() * 1000;
                    updateTimeDisplay();
                    updateActiveAnnotations();
                });
            }

            player.on('play', () => {
                state.isPlaying = true;
                document.getElementById('play-btn').innerHTML = '&#10074;&#10074;';
                if (wavesurfer) wavesurfer.play();
            });

            player.on('pause', () => {
                state.isPlaying = false;
                document.getElementById('play-btn').innerHTML = '&#9654;';
                if (wavesurfer) wavesurfer.pause();
            });

            // Load annotations
            await loadAnnotations();
        }

        function initWaveform() {
            const theme = document.documentElement.getAttribute('data-theme') || 'dark';
            const waveColor = theme === 'light' ? '#cbd5e1' : '#4a4a6a';
            const progressColor = theme === 'light' ? '#ff4b4b' : '#e94560';

            wavesurfer = WaveSurfer.create({
                container: '#waveform',
                waveColor: waveColor,
                progressColor: progressColor,
                cursorColor: progressColor,
                height: 80,
                barWidth: 2,
                barGap: 1,
                responsive: true,
                interact: true,
                url: '/media',
            });

            wavesurfer.on('interaction', (time) => {
                const seekTime = time;
                player.currentTime(seekTime);
                state.currentTime = seekTime * 1000;
                updateTimeDisplay();
            });

            wavesurfer.on('ready', () => {
                renderMarkers();
            });
        }

        // ==========================================================================
        // Time Display & Formatting
        // ==========================================================================
        function formatTime(ms) {
            const hours = Math.floor(ms / 3600000);
            const minutes = Math.floor((ms % 3600000) / 60000);
            const seconds = Math.floor((ms % 60000) / 1000);
            const milliseconds = Math.floor(ms % 1000);
            return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(milliseconds).padStart(3, '0')}`;
        }

        function formatTimeShort(ms) {
            const minutes = Math.floor(ms / 60000);
            const seconds = Math.floor((ms % 60000) / 1000);
            return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }

        function updateTimeDisplay() {
            document.getElementById('current-time').textContent = formatTime(state.currentTime);
            document.getElementById('duration').textContent = formatTime(state.duration);
            document.getElementById('input-time').textContent = formatTime(state.currentTime);

            // Update wavesurfer position
            if (wavesurfer && state.duration > 0) {
                const progress = state.currentTime / state.duration;
                wavesurfer.seekTo(progress);
            }
        }

        // ==========================================================================
        // Playback Controls
        // ==========================================================================
        function togglePlay() {
            if (state.isPlaying) {
                player.pause();
            } else {
                player.play();
            }
        }

        function stepFrame(direction) {
            const frameDuration = 1000 / state.fps;
            const newTimeMs = state.currentTime + (direction * frameDuration);
            const clampedMs = Math.max(0, Math.min(newTimeMs, state.duration));
            const newTimeSec = clampedMs / 1000;

            // Update state immediately for responsive repeated stepping
            state.currentTime = clampedMs;
            updateTimeDisplay();

            // Then sync the player
            player.currentTime(newTimeSec);
        }

        function setInPoint() {
            state.inPoint = state.currentTime;
            document.getElementById('in-point').textContent = formatTimeShort(state.inPoint);
            document.getElementById('in-point').classList.add('active');
            updateRangeIndicator();
            showToast('In point set');
        }

        function setOutPoint() {
            state.outPoint = state.currentTime;
            document.getElementById('out-point').textContent = formatTimeShort(state.outPoint);
            document.getElementById('out-point').classList.add('active');
            updateRangeIndicator();
            showToast('Out point set');
        }

        function clearRange() {
            state.inPoint = null;
            state.outPoint = null;
            document.getElementById('in-point').textContent = '--:--';
            document.getElementById('out-point').textContent = '--:--';
            document.getElementById('in-point').classList.remove('active');
            document.getElementById('out-point').classList.remove('active');
            updateRangeIndicator();
        }

        function updateRangeIndicator() {
            const indicator = document.getElementById('range-indicator');
            if (state.inPoint !== null && state.outPoint !== null) {
                indicator.textContent = `(Range: ${formatTimeShort(state.outPoint - state.inPoint)})`;
            } else if (state.inPoint !== null) {
                indicator.textContent = '(Range start set)';
            } else {
                indicator.textContent = '';
            }
        }

        // ==========================================================================
        // Annotation Management
        // ==========================================================================
        async function loadAnnotations() {
            try {
                const response = await fetch('/api/annotations');
                const data = await response.json();
                state.annotations = data.annotations || [];
                renderAnnotationList();
                renderMarkers();
                document.getElementById('annotation-count').textContent = state.annotations.length;
            } catch (error) {
                console.error('Failed to load annotations:', error);
            }
        }

        async function submitAnnotation() {
            const input = document.getElementById('annotation-input');
            const text = input.value.trim();

            if (!text) {
                showToast('Please enter annotation text', 'error');
                return;
            }

            const annotation = {
                start_ms: state.inPoint !== null ? state.inPoint : Math.round(state.currentTime),
                end_ms: state.outPoint !== null ? state.outPoint : null,
                text: text,
                category: document.getElementById('category-select').value,
            };

            try {
                const response = await fetch('/api/annotations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(annotation),
                });

                if (response.ok) {
                    input.value = '';
                    clearRange();
                    await loadAnnotations();
                    showToast('Annotation added');
                } else {
                    showToast('Failed to add annotation', 'error');
                }
            } catch (error) {
                console.error('Failed to submit annotation:', error);
                showToast('Failed to add annotation', 'error');
            }
        }

        async function deleteAnnotation(id) {
            if (!confirm('Delete this annotation?')) return;

            try {
                const response = await fetch(`/api/annotations/${id}`, {
                    method: 'DELETE',
                });

                if (response.ok) {
                    await loadAnnotations();
                    showToast('Annotation deleted');
                }
            } catch (error) {
                console.error('Failed to delete annotation:', error);
            }
        }

        async function resolveAnnotation(id) {
            try {
                const response = await fetch(`/api/annotations/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'resolved' }),
                });

                if (response.ok) {
                    await loadAnnotations();
                    showToast('Annotation resolved');
                }
            } catch (error) {
                console.error('Failed to resolve annotation:', error);
            }
        }

        function seekToAnnotation(annotation) {
            player.currentTime(annotation.start_ms / 1000);
            state.activeAnnotation = annotation.id;
            renderAnnotationList();
        }

        function updateActiveAnnotations() {
            const time = state.currentTime;
            let foundActive = null;

            for (const ann of state.annotations) {
                const endMs = ann.end_ms || (ann.start_ms + 500);
                if (time >= ann.start_ms && time <= endMs) {
                    foundActive = ann.id;
                    break;
                }
            }

            if (foundActive !== state.activeAnnotation) {
                state.activeAnnotation = foundActive;
                renderAnnotationList();
            }
        }

        function renderAnnotationList() {
            const container = document.getElementById('annotation-list');

            if (state.annotations.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                        </svg>
                        <p>No annotations yet</p>
                        <p>Start typing while watching to add one</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = state.annotations.map(ann => `
                <div class="annotation-item ${ann.id === state.activeAnnotation ? 'active' : ''} ${ann.status === 'resolved' ? 'resolved' : ''}"
                     onclick="seekToAnnotation(${JSON.stringify(ann).replace(/"/g, '&quot;')})">
                    <div class="annotation-header">
                        <span class="annotation-time">
                            ${formatTimeShort(ann.start_ms)}${ann.end_ms ? ' - ' + formatTimeShort(ann.end_ms) : ''}
                        </span>
                        <span class="annotation-category">${ann.category}</span>
                    </div>
                    <div class="annotation-text">${escapeHtml(ann.text)}</div>
                    <div class="annotation-meta">
                        <span>${ann.author}</span>
                        <span>${new Date(ann.created_at).toLocaleDateString()}</span>
                    </div>
                    <div class="annotation-actions">
                        <button class="resolve" onclick="event.stopPropagation(); resolveAnnotation('${ann.id}')">
                            ${ann.status === 'resolved' ? 'Reopen' : 'Resolve'}
                        </button>
                        <button class="delete" onclick="event.stopPropagation(); deleteAnnotation('${ann.id}')">Delete</button>
                    </div>
                </div>
            `).join('');
        }

        function renderMarkers() {
            if (!wavesurfer || state.duration === 0) return;

            const container = document.getElementById('waveform-markers');
            container.innerHTML = state.annotations.map(ann => {
                const startPercent = (ann.start_ms / state.duration) * 100;
                const endPercent = ann.end_ms
                    ? ((ann.end_ms - ann.start_ms) / state.duration) * 100
                    : 0.3; // Point marker width

                return `
                    <div class="annotation-marker ${ann.end_ms ? '' : 'point'}"
                         style="left: ${startPercent}%; width: ${endPercent}%;"
                         onclick="seekToAnnotation(${JSON.stringify(ann).replace(/"/g, '&quot;')})"
                         title="${escapeHtml(ann.text)}">
                    </div>
                `;
            }).join('');
        }

        // ==========================================================================
        // Export Functions
        // ==========================================================================
        async function exportAnnotations(format) {
            try {
                const response = await fetch(`/api/export/${format}`);

                if (!response.ok) {
                    const data = await response.json();
                    showModal('Export Error', data.error || 'Failed to export annotations');
                    return;
                }

                // Download the file
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const extensions = { vtt: 'vtt', srt: 'srt', json: 'json' };
                a.download = `annotations.${extensions[format] || format}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
                showToast(`Exported as ${format.toUpperCase()}`);
            } catch (error) {
                showModal('Export Error', 'Failed to export annotations. Please try again.');
            }
        }

        function toggleExportMenu() {
            const menu = document.getElementById('export-menu');
            menu.classList.toggle('show');
        }

        function closeExportMenu() {
            const menu = document.getElementById('export-menu');
            menu.classList.remove('show');
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const exportDropdown = document.querySelector('.export-dropdown');
            if (exportDropdown && !exportDropdown.contains(e.target)) {
                closeExportMenu();
            }
            const helpBtn = document.querySelector('.help-btn');
            if (helpBtn && !helpBtn.contains(e.target)) {
                closeHelp();
            }
        });

        function toggleHelp() {
            const dropdown = document.getElementById('help-dropdown');
            dropdown.classList.toggle('show');
        }

        function closeHelp() {
            const dropdown = document.getElementById('help-dropdown');
            dropdown.classList.remove('show');
        }

        // ==========================================================================
        // Modal
        // ==========================================================================
        function showModal(title, message) {
            // Remove existing modal
            const existing = document.getElementById('modal-overlay');
            if (existing) existing.remove();

            const overlay = document.createElement('div');
            overlay.id = 'modal-overlay';
            overlay.className = 'modal-overlay';
            overlay.innerHTML = `
                <div class="modal">
                    <div class="modal-header">${escapeHtml(title)}</div>
                    <div class="modal-body">${escapeHtml(message)}</div>
                    <div class="modal-footer">
                        <button class="btn btn-primary" onclick="closeModal()">OK</button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            // Close on overlay click
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) closeModal();
            });
        }

        function closeModal() {
            const overlay = document.getElementById('modal-overlay');
            if (overlay) overlay.remove();
        }

        // ==========================================================================
        // Frictionless Capture: Auto-pause on typing
        // ==========================================================================
        const annotationInput = document.getElementById('annotation-input');
        let wasPlayingBeforeInput = false;

        annotationInput.addEventListener('focus', () => {
            if (state.isPlaying) {
                wasPlayingBeforeInput = true;
                player.pause();
            }
        });

        annotationInput.addEventListener('input', () => {
            // Capture timestamp on first keystroke
            if (state.inPoint === null && annotationInput.value.length === 1) {
                // Don't auto-set in point, just use current time
            }
        });

        // ==========================================================================
        // Keyboard Shortcuts
        // ==========================================================================
        document.addEventListener('keydown', (e) => {
            // Skip if typing in input
            if (e.target === annotationInput) {
                // Ctrl+Enter to submit
                if (e.ctrlKey && e.key === 'Enter') {
                    e.preventDefault();
                    submitAnnotation();
                }
                // Escape to blur and resume
                if (e.key === 'Escape') {
                    annotationInput.blur();
                    if (wasPlayingBeforeInput) {
                        player.play();
                        wasPlayingBeforeInput = false;
                    }
                }
                return;
            }

            switch (e.key) {
                case ' ':
                    e.preventDefault();
                    togglePlay();
                    break;
                case 'i':
                case 'I':
                    e.preventDefault();
                    setInPoint();
                    break;
                case 'o':
                case 'O':
                    e.preventDefault();
                    setOutPoint();
                    break;
                case '[':
                    e.preventDefault();
                    stepFrame(-1);
                    break;
                case ']':
                    e.preventDefault();
                    stepFrame(1);
                    break;
                case 'ArrowLeft':
                    if (e.altKey) {
                        e.preventDefault();
                        stepFrame(-1);
                    }
                    break;
                case 'ArrowRight':
                    if (e.altKey) {
                        e.preventDefault();
                        stepFrame(1);
                    }
                    break;
                case 'Escape':
                    e.preventDefault();
                    clearRange();
                    break;
            }
        });

        // Global key capture for frictionless typing
        document.addEventListener('keypress', (e) => {
            // If not focused on input and it's a printable character
            if (e.target !== annotationInput && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
                // Focus input and let the character through
                annotationInput.focus();
                // The character will be typed automatically
            }
        });

        // ==========================================================================
        // Theme Management
        // ==========================================================================
        function getPreferredTheme() {
            const stored = localStorage.getItem('montaigne-theme');
            if (stored) return stored;
            return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
        }

        function setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('montaigne-theme', theme);

            // Update waveform colors if initialized
            if (wavesurfer) {
                const waveColor = theme === 'light' ? '#cbd5e1' : '#4a4a6a';
                const progressColor = theme === 'light' ? '#ff4b4b' : '#e94560';
                wavesurfer.setOptions({
                    waveColor: waveColor,
                    progressColor: progressColor,
                    cursorColor: progressColor,
                });
            }
        }

        function toggleTheme() {
            const current = document.documentElement.getAttribute('data-theme') || 'dark';
            const next = current === 'dark' ? 'light' : 'dark';
            setTheme(next);
            showToast(`Switched to ${next} mode`);
        }

        // Initialize theme on page load (before DOMContentLoaded to prevent flash)
        (function() {
            const theme = getPreferredTheme();
            document.documentElement.setAttribute('data-theme', theme);
        })();

        // ==========================================================================
        // Utilities
        // ==========================================================================
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function showToast(message, type = 'success') {
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            document.body.appendChild(toast);

            setTimeout(() => {
                toast.remove();
            }, 3000);
        }

        // ==========================================================================
        // File Upload Handling
        // ==========================================================================
        const dropzone = document.getElementById('upload-dropzone');
        const playerSection = document.getElementById('player-section');
        const fileInput = document.getElementById('file-input');
        const uploadProgress = document.getElementById('upload-progress');
        const progressBarFill = document.getElementById('progress-bar-fill');
        const uploadStatus = document.getElementById('upload-status');

        // Drag and drop handlers
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                uploadFile(files[0]);
            }
        });

        // Click to select file
        dropzone.addEventListener('click', (e) => {
            if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'INPUT') {
                fileInput.click();
            }
        });

        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                uploadFile(file);
            }
        }

        async function uploadFile(file) {
            uploadProgress.classList.add('active');
            progressBarFill.style.width = '0%';
            uploadStatus.textContent = 'Uploading...';

            const formData = new FormData();
            formData.append('file', file);

            try {
                const xhr = new XMLHttpRequest();

                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        progressBarFill.style.width = percent + '%';
                        uploadStatus.textContent = `Uploading... ${percent}%`;
                    }
                });

                xhr.addEventListener('load', async () => {
                    if (xhr.status === 200) {
                        const response = JSON.parse(xhr.responseText);
                        uploadStatus.textContent = 'Processing...';
                        progressBarFill.style.width = '100%';

                        // Hide dropzone, show player
                        dropzone.classList.add('hidden');
                        playerSection.classList.remove('hidden');

                        // Initialize player with new media
                        await initPlayer();
                        showToast(`Loaded: ${response.filename}`);
                    } else {
                        const error = JSON.parse(xhr.responseText);
                        uploadStatus.textContent = `Error: ${error.error}`;
                        progressBarFill.style.width = '0%';
                        showToast(error.error, 'error');
                    }
                });

                xhr.addEventListener('error', () => {
                    uploadStatus.textContent = 'Upload failed';
                    progressBarFill.style.width = '0%';
                    showToast('Upload failed', 'error');
                });

                xhr.open('POST', '/api/upload');
                xhr.send(formData);
            } catch (error) {
                uploadStatus.textContent = 'Upload failed';
                showToast('Upload failed: ' + error.message, 'error');
            }
        }

        // ==========================================================================
        // Initialize
        // ==========================================================================
        async function init() {
            // Check if media is already loaded
            try {
                const response = await fetch('/api/status');
                const status = await response.json();

                if (status.has_media) {
                    // Media is loaded, show player
                    dropzone.classList.add('hidden');
                    playerSection.classList.remove('hidden');
                    await initPlayer();
                } else {
                    // No media, show upload dropzone
                    dropzone.classList.remove('hidden');
                    playerSection.classList.add('hidden');
                }
            } catch (error) {
                console.error('Failed to check status:', error);
                // Show dropzone by default on error
                dropzone.classList.remove('hidden');
                playerSection.classList.add('hidden');
            }
        }

        document.addEventListener('DOMContentLoaded', init);
    </script>
</body>
</html>
"""


def run_server(
    media_path: Optional[Path] = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: Optional[Path] = None,
    open_browser: bool = True,
):
    """Run the annotation server."""
    app = create_app(media_path, db_path)

    url = f"http://{host}:{port}"
    logger.info("Starting annotation server at %s", url)
    if media_path:
        logger.info("Media: %s", media_path.name)
    else:
        logger.info("No media loaded - upload via web interface")

    if open_browser:
        import webbrowser
        import threading

        def open_browser_delayed():
            import time

            time.sleep(1)
            webbrowser.open(url)

        threading.Thread(target=open_browser_delayed, daemon=True).start()

    app.run(host=host, port=port, debug=False, threaded=True)
