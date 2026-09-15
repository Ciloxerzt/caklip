#!/usr/bin/env python3
"""
Audio Extraction Module - Extract audio from video files using FFmpeg
Uses deterministic FFmpeg processing, no AI involved
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any


def extract_audio(video_path: Path, audio_output: Path) -> Dict[str, Any]:
    """Extract audio track from video file to WAV format.
    
    Uses FFmpeg with high-quality audio extraction.
    Output is always WAV (PCM) for best compatibility with transcription.
    """
    try:
        audio_output.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "ffmpeg", "-v", "quiet",
            "-i", str(video_path.resolve()),
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # Uncompressed 16-bit PCM
            "-ar", "16000",  # 16kHz sample rate (good for speech)
            "-ac", "1",  # Mono
            "-threads", "0",  # Use all available cores
            str(audio_output.resolve())
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr,
                "audio_path": None
            }
        
        if not audio_output.exists():
            return {
                "success": False,
                "error": "Audio file not created despite success exit code",
                "audio_path": None
            }
        
        # Get audio info
        info_cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(audio_output.resolve())
        ]
        info_result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
        
        info = {}
        if info_result.returncode == 0:
            info = json.loads(info_result.stdout)
        
        return {
            "success": True,
            "error": None,
            "audio_path": str(audio_output.resolve()),
            "duration": info.get("format", {}).get("duration"),
            "sample_rate": info.get("streams", [{}])[0].get("sample_rate") if info.get("streams") else None,
            "channels": info.get("streams", [{}])[0].get("channels") if info.get("streams") else None,
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "FFmpeg extraction timed out",
            "audio_path": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "audio_path": None
        }


def get_audio_only_duration(video_path: Path) -> Optional[float]:
    """Get just the audio duration from a video file without full extraction."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1",
        str(video_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    
    return None


def validate_audio_file(audio_path: Path) -> Dict[str, Any]:
    """Validate that an extracted audio file is usable for transcription."""
    if not audio_path.exists():
        return {"valid": False, "error": "Audio file does not exist"}
    
    # Check minimum duration (at least 1 second)
    import os
    size = os.path.getsize(audio_path)
    if size < 1000:  # Less than 1KB is likely corrupt or empty
        return {"valid": False, "error": "Audio file too small (likely corrupt)"}
    
    # Try to probe with ffprobe
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1",
        str(audio_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            if duration and duration > 0:
                return {"valid": True, "duration": duration}
    except Exception as e:
        pass
    
    # If ffprobe failed, check file size as rough indicator
    if size > 5000:  # At least 5KB
        return {"valid": True, "duration": None}
    
    return {"valid": False, "error": "Could not validate audio file"}