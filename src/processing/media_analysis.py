#!/usr/bin/env python3
"""
Media Analysis Module - FFmpeg-based deterministic processing
Handles video metadata, analysis, and format detection without AI
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def run_ffmpeg(probe_cmd: list) -> Dict[str, Any]:
    """Run ffmpeg probe command and return parsed JSON."""
    try:
        result = subprocess.run(
            ["ffmpeg"] + probe_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            return {"error": result.stderr}
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        return {"error": str(e)}


def probe_video(video_path: Path) -> Dict[str, Any]:
    """Probe a video file to extract metadata."""
    cmd = [
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        str(video_path.resolve())
    ]
    return run_ffmpeg(cmd)


def get_video_info(video_path: Path) -> Dict[str, Any]:
    """Get comprehensive video file information."""
    probe = probe_video(video_path)
    
    if "error" in probe:
        return {"error": probe["error"]}
    
    info = {
        "exists": True,
        "path": str(video_path.resolve()),
        "size_bytes": video_path.stat().st_size,
    }
    
    # Extract stream information
    streams = probe.get("streams", [])
    
    video_stream = None
    audio_streams = []
    
    for stream in streams:
        codec_type = stream.get("codec_type", "")
        if codec_type == "video":
            video_stream = stream
        elif codec_type == "audio":
            audio_streams.append(stream)
    
    if video_stream:
        info.update({
            "duration": video_stream.get("duration"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "r_frame_rate": video_stream.get("r_frame_rate"),
            "codec_name": video_stream.get("codec_name"),
            "bit_rate": video_stream.get("bit_rate"),
        })
    
    if audio_streams:
        info["audio_tracks"] = len(audio_streams)
        for i, aud in enumerate(audio_streams):
            info[f"audio_{i}"] = {
                "codec": aud.get("codec_name"),
                "channels": aud.get("channels"),
                "sample_rate": aud.get("sample_rate"),
            }
    
    # Get format-level info
    if "format" in probe:
        fmt = probe["format"]
        info.update({
            "format": fmt.get("format_name"),
            "container": fmt.get("container"),
            "duration": fmt.get("duration"),
            "size": fmt.get("size"),
            "bit_rate": fmt.get("bit_rate"),
        })
    
    # Rotation/orientation
    rotation = 0
    if "tags" in video_stream:
        rotation_str = video_stream["tags"].get("rotate", "0")
        try:
            rotation = int(rotation_str)
        except ValueError:
            rotation = 0
    info["rotation"] = rotation
    
    # Aspect ratio calculation
    if video_stream and video_stream.get("width") and video_stream.get("height"):
        w, h = video_stream["width"], video_stream["height"]
        # Simplified aspect ratio
        if w > 0 and h > 0:
            ratio = w / h
            info["aspect_ratio"] = round(ratio, 2)
            info["display_aspect"] = "16:9" if ratio >= 1.77 else "4:3" if ratio >= 1.2 else "other"
        else:
            info["aspect_ratio"] = None
            info["display_aspect"] = None
    else:
        info["aspect_ratio"] = None
        info["display_aspect"] = None
    
    return info


def detect_codecs(video_path: Path) -> Dict[str, str]:
    """Detect video and audio codecs."""
    probe = probe_video([
        "-show_entries", "stream=codec_name,codec_type",
        "-of", "csv=p=0",
        str(video_path.resolve())
    ])
    
    result = {"video": None, "audio": []}
    if "error" in probe:
        return result
    
    lines = probe.strip().split("\n")
    for line in lines:
        parts = line.split(",", 1)
        if len(parts) == 2:
            codec_type, codec_name = parts
            if codec_type == "video":
                result["video"] = codec_name
            elif codec_type == "audio":
                result["audio"].append(codec_name)
    
    return result


def check_hardware_support() -> Dict[str, bool]:
    """Check available hardware acceleration."""
    result = {"cuda": False, "qsv": False, "amf": False, "vaapi": False}
    
    try:
        # Check for NVIDIA CUDA
        res = subprocess.run(
            ["ffmpeg", "-hwaccels"],
            capture_output=True, text=True, timeout=10
        )
        if "cuda" in res.stdout.lower():
            result["cuda"] = True
    except Exception:
        pass
    
    try:
        # Check for Intel QSV
        res = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True, text=True, timeout=10
        )
        if "h264_qsv" in res.stdout:
            result["qsv"] = True
    except Exception:
        pass
    
    try:
        # Check for AMF
        res = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True, text=True, timeout=10
        )
        if "h264_amf" in res.stdout:
            result["amf"] = True
    except Exception:
        pass
    
    try:
        # Check for VAAPI
        res = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True, text=True, timeout=10
        )
        if "h264_vaapi" in res.stdout:
            result["vaapi"] = True
    except Exception:
        pass
    
    return result


def validate_video_format(video_path: Path) -> Dict[str, Any]:
    """Validate that a video file is supported and healthy."""
    info = get_video_info(video_path)
    
    if "error" in info:
        return {"valid": False, "error": info["error"]}
    
    # Check minimum requirements
    issues = []
    
    duration = info.get("duration")
    if not duration or float(duration) <= 0:
        issues.append("Invalid or missing duration")
    
    width = info.get("width")
    height = info.get("height")
    if not width or not height or int(width) <= 0 or int(height) <= 0:
        issues.append("Invalid resolution")
    
    # Supported containers
    container = info.get("container", "")
    supported = ["mp4", "mov", "mkv", "webm", "avi"]
    if container and container.lower() not in supported:
        issues.append(f"Unsupported container: {container}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "info": info
    }