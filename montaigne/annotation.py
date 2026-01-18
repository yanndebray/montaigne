"""
Video/Audio Annotation Tool for Montaigne.

Frame-accurate annotation system with:
- Millisecond-precision timestamps (integers to avoid floating-point drift)
- Local SQLite storage for zero-latency persistence
- WebVTT/SRT export for NLE interoperability
- Category-based filtering and organization
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class AnnotationCategory(str, Enum):
    """Annotation categories for filtering and organization."""
    GENERAL = "general"
    PACING = "pacing"
    PRONUNCIATION = "pronunciation"
    AUDIO_QUALITY = "audio_quality"
    TIMING = "timing"
    CONTENT = "content"
    TECHNICAL = "technical"


class AnnotationStatus(str, Enum):
    """Status tracking for annotation workflow."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


@dataclass
class Annotation:
    """
    Core annotation data model.

    Uses milliseconds as integers for frame-accurate sync without floating-point drift.
    Shape coordinates are normalized percentages (0.0-1.0) for resolution-independent overlays.
    """
    id: str
    media_id: str
    start_ms: int  # Integer milliseconds for precision
    end_ms: Optional[int]  # None for point-in-time annotations
    text: str
    category: AnnotationCategory = AnnotationCategory.GENERAL
    status: AnnotationStatus = AnnotationStatus.OPEN
    author: str = "anonymous"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    # Normalized shape coordinates (percentages 0.0-1.0) for resolution-independent overlays
    shape: Optional[dict] = None  # {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4}
    parent_id: Optional[str] = None  # For threaded comments
    metadata: dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        media_id: str,
        start_ms: int,
        text: str,
        end_ms: Optional[int] = None,
        category: AnnotationCategory = AnnotationCategory.GENERAL,
        author: str = "anonymous",
        shape: Optional[dict] = None,
        parent_id: Optional[str] = None,
    ) -> "Annotation":
        """Factory method to create a new annotation with generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            media_id=media_id,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            category=category,
            author=author,
            shape=shape,
            parent_id=parent_id,
        )

    def is_range(self) -> bool:
        """Check if this is a range annotation vs point-in-time."""
        return self.end_ms is not None and self.end_ms > self.start_ms

    def contains_time(self, time_ms: int) -> bool:
        """Check if the given time falls within this annotation's range."""
        if self.end_ms is None:
            # Point annotation: match within 500ms window
            return abs(time_ms - self.start_ms) <= 500
        return self.start_ms <= time_ms <= self.end_ms

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["category"] = self.category.value
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Annotation":
        """Create annotation from dictionary."""
        data = data.copy()
        data["category"] = AnnotationCategory(data.get("category", "general"))
        data["status"] = AnnotationStatus(data.get("status", "open"))
        return cls(**data)


class AnnotationStore:
    """
    SQLite-based local storage for annotations.

    Provides zero-latency persistence with SQL query capabilities.
    Uses second-bucketing optimization for O(1) time lookups during playback.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize annotation store with optional custom database path."""
        if db_path is None:
            db_path = Path.home() / ".montaigne" / "annotations.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Second-bucketing cache for O(1) time lookups
        self._bucket_cache: dict[str, dict[int, list[str]]] = {}

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS annotations (
                    id TEXT PRIMARY KEY,
                    media_id TEXT NOT NULL,
                    start_ms INTEGER NOT NULL,
                    end_ms INTEGER,
                    text TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    status TEXT DEFAULT 'open',
                    author TEXT DEFAULT 'anonymous',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    shape TEXT,
                    parent_id TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_media_time
                ON annotations(media_id, start_ms)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_media_status
                ON annotations(media_id, status)
            """)
            conn.commit()

    def save(self, annotation: Annotation) -> Annotation:
        """Save or update an annotation."""
        annotation.updated_at = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO annotations
                (id, media_id, start_ms, end_ms, text, category, status,
                 author, created_at, updated_at, shape, parent_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                annotation.id,
                annotation.media_id,
                annotation.start_ms,
                annotation.end_ms,
                annotation.text,
                annotation.category.value,
                annotation.status.value,
                annotation.author,
                annotation.created_at,
                annotation.updated_at,
                json.dumps(annotation.shape) if annotation.shape else None,
                annotation.parent_id,
                json.dumps(annotation.metadata),
            ))
            conn.commit()

        # Invalidate bucket cache for this media
        self._bucket_cache.pop(annotation.media_id, None)

        return annotation

    def get(self, annotation_id: str) -> Optional[Annotation]:
        """Get annotation by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM annotations WHERE id = ?",
                (annotation_id,)
            ).fetchone()

            if row:
                return self._row_to_annotation(row)
        return None

    def delete(self, annotation_id: str) -> bool:
        """Delete an annotation."""
        with sqlite3.connect(self.db_path) as conn:
            # Get media_id for cache invalidation
            row = conn.execute(
                "SELECT media_id FROM annotations WHERE id = ?",
                (annotation_id,)
            ).fetchone()

            if row:
                conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
                conn.commit()
                self._bucket_cache.pop(row[0], None)
                return True
        return False

    def get_by_media(
        self,
        media_id: str,
        status: Optional[AnnotationStatus] = None,
        category: Optional[AnnotationCategory] = None,
    ) -> list[Annotation]:
        """Get all annotations for a media file with optional filters."""
        query = "SELECT * FROM annotations WHERE media_id = ?"
        params: list = [media_id]

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if category:
            query += " AND category = ?"
            params.append(category.value)

        query += " ORDER BY start_ms"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_annotation(row) for row in rows]

    def get_at_time(self, media_id: str, time_ms: int) -> list[Annotation]:
        """
        Get annotations visible at a specific time using second-bucketing.

        Optimized for 60fps playback by using O(1) bucket lookups instead of O(n) scans.
        """
        # Build bucket cache if needed
        if media_id not in self._bucket_cache:
            self._build_bucket_cache(media_id)

        # Get the second bucket
        second = time_ms // 1000
        bucket = self._bucket_cache.get(media_id, {})

        # Check current and adjacent buckets for range annotations
        annotation_ids = set()
        for s in [second - 1, second, second + 1]:
            annotation_ids.update(bucket.get(s, []))

        # Filter to annotations actually containing this time
        result = []
        for ann_id in annotation_ids:
            ann = self.get(ann_id)
            if ann and ann.contains_time(time_ms):
                result.append(ann)

        return sorted(result, key=lambda a: a.start_ms)

    def _build_bucket_cache(self, media_id: str):
        """Build second-bucket cache for a media file."""
        annotations = self.get_by_media(media_id)
        buckets: dict[int, list[str]] = {}

        for ann in annotations:
            # Add to all seconds this annotation spans
            start_sec = ann.start_ms // 1000
            end_sec = (ann.end_ms or ann.start_ms) // 1000

            for sec in range(start_sec, end_sec + 1):
                if sec not in buckets:
                    buckets[sec] = []
                buckets[sec].append(ann.id)

        self._bucket_cache[media_id] = buckets

    def _row_to_annotation(self, row: sqlite3.Row) -> Annotation:
        """Convert database row to Annotation object."""
        return Annotation(
            id=row["id"],
            media_id=row["media_id"],
            start_ms=row["start_ms"],
            end_ms=row["end_ms"],
            text=row["text"],
            category=AnnotationCategory(row["category"]),
            status=AnnotationStatus(row["status"]),
            author=row["author"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            shape=json.loads(row["shape"]) if row["shape"] else None,
            parent_id=row["parent_id"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )


# =============================================================================
# Export Functions
# =============================================================================

def ms_to_timecode(ms: int, format: str = "vtt") -> str:
    """
    Convert milliseconds to timecode string.

    Args:
        ms: Time in milliseconds
        format: "vtt" for WebVTT (HH:MM:SS.mmm) or "srt" for SubRip (HH:MM:SS,mmm)

    Returns:
        Formatted timecode string
    """
    hours, remainder = divmod(ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)

    separator = "." if format == "vtt" else ","
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}{separator}{int(milliseconds):03d}"


def export_to_webvtt(
    annotations: list[Annotation],
    output_path: Path,
    include_metadata: bool = True,
) -> Path:
    """
    Export annotations to WebVTT format.

    WebVTT is the native browser format for video captions/subtitles.
    """
    lines = ["WEBVTT", ""]

    for i, ann in enumerate(sorted(annotations, key=lambda a: a.start_ms), 1):
        # Cue identifier
        lines.append(f"{i}")

        # Timing line
        start = ms_to_timecode(ann.start_ms, "vtt")
        end = ms_to_timecode(ann.end_ms or (ann.start_ms + 2000), "vtt")
        lines.append(f"{start} --> {end}")

        # Cue text with optional metadata
        text = ann.text
        if include_metadata:
            text = f"[{ann.category.value.upper()}] {text}"
            if ann.status != AnnotationStatus.OPEN:
                text += f" ({ann.status.value})"
        lines.append(text)
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def export_to_srt(
    annotations: list[Annotation],
    output_path: Path,
    include_metadata: bool = True,
) -> Path:
    """
    Export annotations to SRT (SubRip) format.

    SRT is widely supported by video editors like Premiere, DaVinci Resolve.
    """
    lines = []

    for i, ann in enumerate(sorted(annotations, key=lambda a: a.start_ms), 1):
        # Sequence number
        lines.append(str(i))

        # Timing line
        start = ms_to_timecode(ann.start_ms, "srt")
        end = ms_to_timecode(ann.end_ms or (ann.start_ms + 2000), "srt")
        lines.append(f"{start} --> {end}")

        # Subtitle text
        text = ann.text
        if include_metadata:
            text = f"[{ann.category.value.upper()}] {text}"
            if ann.status != AnnotationStatus.OPEN:
                text += f" ({ann.status.value})"
        lines.append(text)
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def export_to_json(
    annotations: list[Annotation],
    output_path: Path,
) -> Path:
    """Export annotations to JSON format for programmatic access."""
    data = {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "count": len(annotations),
        "annotations": [ann.to_dict() for ann in annotations],
    }

    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return output_path


def import_from_json(json_path: Path, store: AnnotationStore) -> list[Annotation]:
    """Import annotations from JSON file into store."""
    data = json.loads(json_path.read_text(encoding="utf-8"))

    annotations = []
    for ann_data in data.get("annotations", []):
        ann = Annotation.from_dict(ann_data)
        store.save(ann)
        annotations.append(ann)

    return annotations


# =============================================================================
# Utility Functions
# =============================================================================

def get_frame_duration_ms(fps: float) -> float:
    """Get duration of a single frame in milliseconds."""
    return 1000.0 / fps


def snap_to_frame(time_ms: int, fps: float) -> int:
    """Snap a time value to the nearest frame boundary."""
    frame_duration = get_frame_duration_ms(fps)
    frame_number = round(time_ms / frame_duration)
    return int(frame_number * frame_duration)


def get_media_id(media_path: Path) -> str:
    """Generate a consistent media ID from file path."""
    # Use filename + size + mtime for uniqueness
    stat = media_path.stat()
    return f"{media_path.name}_{stat.st_size}_{int(stat.st_mtime)}"
