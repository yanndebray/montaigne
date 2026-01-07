"""Graphical user interface for Montaigne media processing toolkit."""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import Optional, Callable
import queue


class OutputRedirector:
    """Redirect stdout/stderr to a queue for GUI display."""

    def __init__(self, output_queue: queue.Queue):
        self.queue = output_queue

    def write(self, text):
        self.queue.put(text)

    def flush(self):
        pass


class MontaigneGUI:
    """Main GUI application for Montaigne toolkit."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Montaigne - Presentation Video Generator")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        # Output queue for thread-safe logging
        self.output_queue = queue.Queue()

        # Variables
        self.pdf_path = tk.StringVar()
        self.script_path = tk.StringVar()
        self.images_dir = tk.StringVar()
        self.audio_dir = tk.StringVar()
        self.output_path = tk.StringVar()
        self.voice = tk.StringVar(value="Orus")
        self.resolution = tk.StringVar(value="1920:1080")
        self.context = tk.StringVar()

        # Processing state
        self.is_processing = False

        self._create_widgets()
        self._check_queue()

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Montaigne",
            font=("Helvetica", 24, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 5))

        subtitle_label = ttk.Label(
            main_frame,
            text="Transform presentations into narrated videos",
            font=("Helvetica", 10)
        )
        subtitle_label.grid(row=0, column=0, pady=(30, 10))

        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky="ew", pady=10)

        # Create tabs
        self._create_video_tab()
        self._create_steps_tab()
        self._create_settings_tab()

        # Output area
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="5")
        output_frame.grid(row=2, column=0, sticky="nsew", pady=10)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            height=12,
            font=("Consolas", 9),
            state="disabled"
        )
        self.output_text.grid(row=0, column=0, sticky="nsew")

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, sticky="ew")

        self.run_btn = ttk.Button(
            btn_frame,
            text="Generate Video",
            command=self._run_video_pipeline,
            style="Accent.TButton"
        )
        self.run_btn.pack(side="left", padx=5)

        ttk.Button(
            btn_frame,
            text="Clear Output",
            command=self._clear_output
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_frame,
            text="Open Output Folder",
            command=self._open_output_folder
        ).pack(side="right", padx=5)

    def _create_video_tab(self):
        """Create the main video generation tab."""
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="Quick Video")

        # PDF selection
        ttk.Label(tab, text="PDF File:").grid(row=0, column=0, sticky="w", pady=5)
        pdf_frame = ttk.Frame(tab)
        pdf_frame.grid(row=0, column=1, sticky="ew", pady=5)
        pdf_frame.columnconfigure(0, weight=1)

        ttk.Entry(pdf_frame, textvariable=self.pdf_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(pdf_frame, text="Browse", command=self._browse_pdf).grid(row=0, column=1, padx=(5, 0))

        # Script (optional)
        ttk.Label(tab, text="Script (optional):").grid(row=1, column=0, sticky="w", pady=5)
        script_frame = ttk.Frame(tab)
        script_frame.grid(row=1, column=1, sticky="ew", pady=5)
        script_frame.columnconfigure(0, weight=1)

        ttk.Entry(script_frame, textvariable=self.script_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(script_frame, text="Browse", command=self._browse_script).grid(row=0, column=1, padx=(5, 0))

        # Output path
        ttk.Label(tab, text="Output Video:").grid(row=2, column=0, sticky="w", pady=5)
        output_frame = ttk.Frame(tab)
        output_frame.grid(row=2, column=1, sticky="ew", pady=5)
        output_frame.columnconfigure(0, weight=1)

        ttk.Entry(output_frame, textvariable=self.output_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(output_frame, text="Browse", command=self._browse_output).grid(row=0, column=1, padx=(5, 0))

        # Voice selection
        ttk.Label(tab, text="Voice:").grid(row=3, column=0, sticky="w", pady=5)
        voice_combo = ttk.Combobox(
            tab,
            textvariable=self.voice,
            values=["Puck", "Charon", "Kore", "Fenrir", "Aoede", "Orus"],
            state="readonly",
            width=15
        )
        voice_combo.grid(row=3, column=1, sticky="w", pady=5)

        # Resolution
        ttk.Label(tab, text="Resolution:").grid(row=4, column=0, sticky="w", pady=5)
        res_combo = ttk.Combobox(
            tab,
            textvariable=self.resolution,
            values=["1920:1080", "1280:720", "3840:2160"],
            width=15
        )
        res_combo.grid(row=4, column=1, sticky="w", pady=5)

        tab.columnconfigure(1, weight=1)

    def _create_steps_tab(self):
        """Create tab for individual steps."""
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="Individual Steps")

        # Step 1: PDF to Images
        step1_frame = ttk.LabelFrame(tab, text="Step 1: Extract PDF", padding="5")
        step1_frame.grid(row=0, column=0, sticky="ew", pady=5)
        step1_frame.columnconfigure(1, weight=1)

        ttk.Button(step1_frame, text="Extract PDF to Images", command=self._run_pdf_extract).grid(row=0, column=0)

        # Step 2: Generate Script
        step2_frame = ttk.LabelFrame(tab, text="Step 2: Generate Script", padding="5")
        step2_frame.grid(row=1, column=0, sticky="ew", pady=5)
        step2_frame.columnconfigure(1, weight=1)

        ttk.Label(step2_frame, text="Context:").grid(row=0, column=0, sticky="w")
        ttk.Entry(step2_frame, textvariable=self.context, width=50).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(step2_frame, text="Generate Script", command=self._run_script_gen).grid(row=0, column=2)

        # Step 3: Generate Audio
        step3_frame = ttk.LabelFrame(tab, text="Step 3: Generate Audio", padding="5")
        step3_frame.grid(row=2, column=0, sticky="ew", pady=5)

        ttk.Button(step3_frame, text="Generate Audio", command=self._run_audio_gen).grid(row=0, column=0)

        # Step 4: Create Video
        step4_frame = ttk.LabelFrame(tab, text="Step 4: Create Video", padding="5")
        step4_frame.grid(row=3, column=0, sticky="ew", pady=5)
        step4_frame.columnconfigure(1, weight=1)

        ttk.Label(step4_frame, text="Images:").grid(row=0, column=0, sticky="w")
        img_entry = ttk.Entry(step4_frame, textvariable=self.images_dir)
        img_entry.grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(step4_frame, text="Browse", command=self._browse_images_dir).grid(row=0, column=2)

        ttk.Label(step4_frame, text="Audio:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        audio_entry = ttk.Entry(step4_frame, textvariable=self.audio_dir)
        audio_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=(5, 0))
        ttk.Button(step4_frame, text="Browse", command=self._browse_audio_dir).grid(row=1, column=2, pady=(5, 0))

        ttk.Button(step4_frame, text="Create Video", command=self._run_video_only).grid(row=2, column=0, pady=(10, 0))

        tab.columnconfigure(0, weight=1)

    def _create_settings_tab(self):
        """Create settings tab."""
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="Settings")

        # API Key status
        api_frame = ttk.LabelFrame(tab, text="Gemini API", padding="10")
        api_frame.grid(row=0, column=0, sticky="ew", pady=5)

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            status = f"Configured (***{api_key[-4:]})"
            status_color = "green"
        else:
            status = "Not configured"
            status_color = "red"

        ttk.Label(api_frame, text=f"Status: {status}").grid(row=0, column=0, sticky="w")

        # ffmpeg status
        ffmpeg_frame = ttk.LabelFrame(tab, text="ffmpeg", padding="10")
        ffmpeg_frame.grid(row=1, column=0, sticky="ew", pady=5)

        from .video import check_ffmpeg
        ffmpeg_status = "Installed" if check_ffmpeg() else "Not found"
        ttk.Label(ffmpeg_frame, text=f"Status: {ffmpeg_status}").grid(row=0, column=0, sticky="w")

        # About
        about_frame = ttk.LabelFrame(tab, text="About", padding="10")
        about_frame.grid(row=2, column=0, sticky="ew", pady=5)

        from . import __version__
        ttk.Label(about_frame, text=f"Montaigne v{__version__}").grid(row=0, column=0, sticky="w")
        ttk.Label(about_frame, text="Media processing toolkit for presentation localization").grid(row=1, column=0, sticky="w")

        tab.columnconfigure(0, weight=1)

    def _browse_pdf(self):
        path = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if path:
            self.pdf_path.set(path)
            # Auto-set output path
            if not self.output_path.get():
                self.output_path.set(str(Path(path).with_suffix(".mp4")))

    def _browse_script(self):
        path = filedialog.askopenfilename(
            title="Select Script",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if path:
            self.script_path.set(path)

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save Video As",
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        if path:
            self.output_path.set(path)

    def _browse_images_dir(self):
        path = filedialog.askdirectory(title="Select Images Directory")
        if path:
            self.images_dir.set(path)

    def _browse_audio_dir(self):
        path = filedialog.askdirectory(title="Select Audio Directory")
        if path:
            self.audio_dir.set(path)

    def _log(self, message: str):
        """Log a message to the output area."""
        self.output_queue.put(message + "\n")

    def _check_queue(self):
        """Check the output queue and update the text widget."""
        try:
            while True:
                message = self.output_queue.get_nowait()
                self.output_text.configure(state="normal")
                self.output_text.insert("end", message)
                self.output_text.see("end")
                self.output_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._check_queue)

    def _clear_output(self):
        """Clear the output text area."""
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

    def _open_output_folder(self):
        """Open the output folder in file explorer."""
        output = self.output_path.get()
        if output:
            folder = Path(output).parent
        elif self.pdf_path.get():
            folder = Path(self.pdf_path.get()).parent
        else:
            folder = Path.cwd()

        if folder.exists():
            os.startfile(str(folder))

    def _set_processing(self, processing: bool):
        """Set the processing state."""
        self.is_processing = processing
        if processing:
            self.progress.start()
            self.run_btn.configure(state="disabled")
        else:
            self.progress.stop()
            self.run_btn.configure(state="normal")

    def _run_in_thread(self, func: Callable, *args):
        """Run a function in a background thread."""
        def wrapper():
            import sys
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = OutputRedirector(self.output_queue)
            sys.stderr = OutputRedirector(self.output_queue)

            try:
                func(*args)
            except Exception as e:
                self._log(f"\nError: {e}")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                self.root.after(0, lambda: self._set_processing(False))

        self._set_processing(True)
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()

    def _run_video_pipeline(self):
        """Run the full video generation pipeline."""
        if not self.pdf_path.get():
            messagebox.showerror("Error", "Please select a PDF file")
            return

        from .video import generate_video_from_pdf

        pdf_path = Path(self.pdf_path.get())
        script_path = Path(self.script_path.get()) if self.script_path.get() else None
        output_path = Path(self.output_path.get()) if self.output_path.get() else None

        self._log(f"Starting video generation from {pdf_path.name}...\n")
        self._run_in_thread(
            generate_video_from_pdf,
            pdf_path,
            script_path,
            output_path,
            self.resolution.get(),
            self.voice.get()
        )

    def _run_pdf_extract(self):
        """Run PDF extraction only."""
        if not self.pdf_path.get():
            messagebox.showerror("Error", "Please select a PDF file")
            return

        from .pdf import extract_pdf_pages

        pdf_path = Path(self.pdf_path.get())
        self._log(f"Extracting pages from {pdf_path.name}...\n")
        self._run_in_thread(extract_pdf_pages, pdf_path)

    def _run_script_gen(self):
        """Run script generation only."""
        if not self.pdf_path.get():
            messagebox.showerror("Error", "Please select a PDF file")
            return

        from .scripts import generate_scripts

        pdf_path = Path(self.pdf_path.get())
        context = self.context.get() or ""
        self._log(f"Generating script from {pdf_path.name}...\n")
        self._run_in_thread(generate_scripts, pdf_path, None, context)

    def _run_audio_gen(self):
        """Run audio generation only."""
        # Find script file
        if self.script_path.get():
            script_path = Path(self.script_path.get())
        elif self.pdf_path.get():
            pdf_path = Path(self.pdf_path.get())
            script_path = pdf_path.parent / f"{pdf_path.stem}_voiceover.md"
        else:
            messagebox.showerror("Error", "Please select a script file")
            return

        if not script_path.exists():
            messagebox.showerror("Error", f"Script not found: {script_path}")
            return

        from .audio import generate_audio

        self._log(f"Generating audio from {script_path.name}...\n")
        self._run_in_thread(generate_audio, script_path, None, self.voice.get())

    def _run_video_only(self):
        """Run video creation from existing images and audio."""
        if not self.images_dir.get() or not self.audio_dir.get():
            messagebox.showerror("Error", "Please select both images and audio directories")
            return

        from .video import generate_video

        images_dir = Path(self.images_dir.get())
        audio_dir = Path(self.audio_dir.get())
        output_path = Path(self.output_path.get()) if self.output_path.get() else None

        self._log(f"Creating video from {images_dir.name} and {audio_dir.name}...\n")
        self._run_in_thread(generate_video, images_dir, audio_dir, output_path, self.resolution.get())


def launch_gui():
    """Launch the Montaigne GUI application."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    root = tk.Tk()

    # Set theme
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    elif "clam" in style.theme_names():
        style.theme_use("clam")

    app = MontaigneGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
