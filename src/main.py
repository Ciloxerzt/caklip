#!/usr/bin/env python3
"""
AI Auto Clipper - Main CLI entry point
Uses FFmpeg for deterministic video processing, AI optional for semantic analysis.
Auto-detects YouTube URLs vs local file paths.
Auto-detects AI model from API key type.
"""

import sys
import subprocess
import json
from pathlib import Path
import argparse


def try_youtube_extract(url):
    """Try to extract YouTube video info using yt-dlp."""
    try:
        result = subprocess.run(
            ["/opt/data/.venv-yt/bin/yt-dlp", "-J", "--quiet", "--no-warnings", url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout:
            try:
                info = json.loads(result.stdout)
                if info.get("id") and info.get("title"):
                    return info
            except (json.JSONDecodeError, TypeError):
                pass
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(
        description="AI Auto Clipper - Deterministic video clip generation with optional AI analysis"
    )
    parser.add_argument(
        "input",
        help="Input video file OR YouTube URL\n- Local file: /path/to/video.mp4\n- YouTube URL: https://youtu.be/VIDEO_ID or https://www.youtube.com/watch?v=VIDEO_ID\n- If YouTube URL fails, falls back to local file processing"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output directory (default: ./output)",
        default="./output"
    )
    parser.add_argument(
        "--model",
        help="AI model to use for semantic analysis (optional, auto-detected from api-key)\n"
             "If api-key provided without --model, model auto-selects based on key type:\n"
             "  - OpenAI key (starts with 'sk-') -> gpt-4o-mini\n"
             "  - Google AI key (starts with 'AIza') -> gemini-1.5-flash\n"
             "  - Anthropic key (starts with 'anthropic-') -> claude-3-haiku\n"
             "  - User can manually override by providing --model explicitly",
        default=None
    )
    parser.add_argument(
        "--api-key",
        help="AI API key (paste only, never logged or exported)",
        default=None
    )
    parser.add_argument(
        "--base-url",
        help="AI API base URL (for OpenAI-compatible APIs, optional)",
        default=None
    )
    parser.add_argument(
        "--preset",
        choices=["youtube", "tiktok", "custom"],
        default="custom",
        help="Video preset format (default: custom)"
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Run without AI (deterministic only - recommended for best results)"
    )
    parser.add_argument(
        "--zoom-factor",
        type=float,
        default=1.0,
        help="Zoom effect factor (1.0 = no zoom, >1.0 = zoom in, default: 1.0)"
    )
    parser.add_argument(
        "--fade-in",
        type=float,
        default=0.5,
        help="Audio fade-in duration in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--fade-out",
        type=float,
        default=0.5,
        help="Audio fade-out duration in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--sound-effect",
        choices=["none", "fade_in", "fade_out", "both", "crossfade", "reverb"],
        default="none",
        help="Sound effect to apply (default: none)"
    )
    parser.add_argument(
        "--audio-preset",
        choices=["speech", "music", "voice"],
        default="speech",
        help="Audio loudness preset (default: speech)"
    )
    parser.add_argument(
        "--face-tracking",
        action="store_true",
        help="Enable OpenCV face tracking for vertical reframing"
    )
    args = parser.parse_args()

    input_path = args.input

    # Auto-detect: if input looks like YouTube URL, try yt-dlp first
    local_file_path = input_path
    youtube_info = None

    if input_path.startswith("http://") or input_path.startswith("https://"):
        print(">>> Detected YouTube URL, attempting to extract video info...")
        youtube_info = try_youtube_extract(input_path)
        if youtube_info:
            print(">>> Successfully extracted: {}".format(youtube_info.get("title", "Unknown")))
            local_file_path = input_path + ".ytdlp-placeholder"
            print(">>> YouTube info extracted, proceeding with processing")
        else:
            print(">>> YouTube URL: yt-dlp could not extract video info")
            print(">>> Falling back to local file processing mode")
            print(">>> Please provide a local video file path, or")
            print(">>> ensure the YouTube video is publicly accessible")
            local_file_path = input_path

    if not Path(local_file_path).exists():
        if input_path.startswith("http://") or input_path.startswith("https://"):
            print("\n" + "="*60)
            print("ERROR: Could not process YouTube URL")
            print("="*60)
            print()
            print("Possible solutions:")
            print("1. Provide a local video file path instead")
            print("2. Ensure the YouTube video is publicly accessible")
            print("3. Check your internet connection and yt-dlp version")
            print("4. Use a different video source")
            print()
            print("Falling back to: caklip /path/to/local/video.mp4")
            sys.exit(1)
        else:
            print("ERROR: Input file not found: {}".format(input_path), file=sys.stderr)
            sys.exit(1)

    # Auto-detect model from API key type
    selected_model = args.model
    api_key = args.api_key
    
    if not selected_model and api_key:
        # Auto-detect model based on API key format/prefix
        key_stripped = api_key.strip()
        # OpenAI keys typically start with "sk-"
        # Google AI Studio keys start with "AIza"
        # Anthropic keys start with "anthropic-"
        if key_stripped.startswith("sk-"):
            selected_model = "gpt-4o-mini"  # OpenAI default
        elif key_stripped.startswith("AIza"):
            selected_model = "gemini-1.5-flash"  # Google default
        elif key_stripped.startswith("anthropic-"):
            selected_model = "claude-3-haiku"  # Anthropic default
        else:
            selected_model = "bai-free"  # Fallback to 9router
    
    if selected_model:
        print("AI Model auto-selected: {}".format(selected_model) + " (based on API key type)")
    else:
        print("AI Disabled: No API key provided")
        selected_model = None

    input_path = Path(local_file_path)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("AI Auto Clipper starting...")
    print("Input: {}".format(input_path))
    if youtube_info:
        print(">>> YouTube Title: {}".format(youtube_info.get("title", "Unknown")))
        print(">>> YouTube Duration: {} seconds".format(youtube_info.get("duration", "Unknown")))
    print("Output: {}".format(output_dir))
    print("AI Model: {}".format(selected_model))
    print("AI Enabled: {}".format(not args.no_ai and selected_model is not None))
    print("Zoom Factor: {}".format(args.zoom_factor))
    print("Fade In: {}s, Fade Out: {}s".format(args.fade_in, args.fade_out))
    print("Sound Effect: {}".format(args.sound_effect))
    print("Audio Preset: {}".format(args.audio_preset))
    print("Face Tracking: {}".format(args.face_tracking))
    print("-" * 50)

    # TODO: Implement the full workflow
    # 1. Media analysis with FFmpeg
    # 2. Audio extraction
    # 3. Transcription (local Whisper or API)
    # 4. AI content analysis (if enabled)
    # 5. Clip scoring (deterministic 7-factor)
    # 6. Clip generation with FFmpeg
    # 7. Smart reframing 16:9->9:16 with face tracking
    # 8. Subtitle generation with word highlighting
    # 9. Final render and export


if __name__ == "__main__":
    main()