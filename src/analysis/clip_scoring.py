#!/usr/bin/env python3
"""
Clip Scoring Module - Deterministic scoring system
Based on the master prompt specifications for clip scoring

Scoring weights (percentages):
Hook strength: 25%
Information value: 20%
Emotional impact: 15%
Curiosity: 15%
Standalone context: 10%
Clarity: 10%
Audio quality: 5%
Total: 100%
"""

import sys
from typing import Dict, Any, List
from .ai_analysis import (
    detect_hook_type,
    analyze_content_value,
    analyze_emotion_indicators,
    compute_clip_score_deterministic,
)


def score_clips(
    segments: List[Dict[str, Any]],
    transcript: str,
    min_duration: float = 10,
    max_duration: float = 60,
) -> List[Dict[str, Any]]:
    """Score all candidate clips from transcript segments.
    
    For each segment, computes a deterministic score based on multiple factors.
    Returns scored clips sorted by score (highest first).
    """
    scored = []
    
    for i, seg in enumerate(segments):
        try:
            start = float(seg.get("start", 0))
            end = float(seg.get("end", 0))
            text = seg.get("text", "").strip()
            
            if not text or end <= start or (end - start) < min_duration:
                continue
            
            if (end - start) > max_duration:
                # Skip clips exceeding max duration, but could trim
                continue
            
            duration = end - start
            
            # Compute deterministic factors
            hook_info = detect_hook_type(text, start, end)
            content_value = analyze_content_value(text)
            emotion_info = analyze_emotion_indicators(text)
            
            # Calculate audio quality metrics from segment
            # Silence ratio: proportion of segment that appears silent
            # Speech density: proportion of non-silent content
            silence_ratio = _calculate_silence_ratio(text)
            speech_density = _calculate_speech_density(text)
            
            # Compute total score
            score_result = compute_clip_score_deterministic(
                hook_info=hook_info,
                content_value=content_value,
                emotion_info=emotion_info,
                silence_ratio=silence_ratio,
                speech_density=speech_density,
                clip_duration=duration,
                min_duration=min_duration,
                max_duration=max_duration,
            )
            
            # Build clip info
            clip_info = {
                "start": start,
                "end": end,
                "duration": duration,
                "text": text,
                "hook_type": hook_info["type"],
                "hook_strength": hook_info["strength"],
                "content_value": content_value["value"],
                "content_confidence": content_value["confidence"],
                "emotion_primary": emotion_info["primary"],
                "emotion_intensity": emotion_info["intensity"],
                "silence_ratio": round(silence_ratio, 3),
                "speech_density": round(speech_density, 3),
                "score": score_result["score"],
                "score_breakdown": score_result["breakdown"],
                "reason": _generate_clip_reason(
                    hook_info, content_value, emotion_info, silence_ratio
                ),
                "categories": _determine_categories(
                    hook_info, content_value, emotion_info
                ),
            }
            
            scored.append(clip_info)
            
        except (ValueError, TypeError) as e:
            print(f"Error scoring segment {i}: {e}", file=sys.stderr)
            continue
    
    # Sort by score (highest first)
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    return scored


def _calculate_silence_ratio(text: str) -> float:
    """Estimate silence ratio from transcript text.
    
    Simple heuristic: ratio of filler/empty words to total words.
    Returns 0.0 to 1.0 where 1.0 = mostly silence.
    """
    if not text:
        return 1.0
    
    # Remove common filler words/phrases (language-aware later)
    filler_patterns = [
        r"\bumm\b", r"\buh\b", r"\bmm\b", r"\bnhm\b",
        r"\blike\b", r"\bkayak\b", r"\bjadi\b", r"\bhmm\b"
    ]
    
    cleaned = text.lower()
    for pattern in filler_patterns:
        import re
        cleaned = re.sub(pattern, "", cleaned)
    
    # Count remaining meaningful words
    words = [w for w in cleaned.split() if len(w) > 1]
    
    if not words:
        return 1.0  # All fillers/silence
    
    # Rough estimate: if many filler words, higher silence ratio
    # This is a simplistic heuristic
    filler_ratio = min(len(cleaned.split()) / max(len(words), 1), 1.0)
    return round(1.0 - filler_ratio, 3)


def _calculate_speech_density(text: str) -> float:
    """Calculate speech density from transcript text.
    
    Returns ratio of actual spoken content to total text.
    Returns 0.0 to 1.0 where 1.0 = very dense speech.
    """
    if not text:
        return 0.0
    
    # Remove common filler words
    filler_words = {"umm", "uh", "mm", "nhm", "hmm", "like", "kayak", "jadi"}
    words = [w for w in text.lower().split() if w not in filler_words]
    
    if not words:
        return 0.0
    
    # Simple density: ratio of non-filler words to total words
    total_words = len(text.lower().split())
    density = len(words) / total_words if total_words > 0 else 0
    
    return round(min(density, 1.0), 3)


def _generate_clip_reason(
    hook_info: Dict[str, Any],
    content_value: Dict[str, Any],
    emotion_info: Dict[str, Any],
    silence_ratio: float,
) -> str:
    """Generate a human-readable reason for clip selection."""
    reasons = []
    
    hook_type = hook_info.get("type", "general")
    hook_strength = hook_info.get("strength", 0)
    
    if hook_strength > 70:
        reasons.append(f"Strong {hook_type} hook")
    elif hook_strength > 40:
        reasons.append(f"Moderate {hook_type} hook")
    
    value = content_value.get("value", "general")
    if value in ("educational", "actionable"):
        reasons.append(f"Educational/informational content")
    
    emotion = emotion_info.get("primary", "neutral")
    if emotion != "neutral":
        reasons.append(f"{emotion} moment")
    
    sr = silence_ratio
    if sr < 0.2:
        reasons.append("Good audio quality")
    elif sr > 0.5:
        reasons.append("Contains filler/long pauses")
    
    if not reasons:
        reasons.append("Selected clip segment")
    
    return " | ".join(reasons[:3])


def _determine_categories(
    hook_info: Dict[str, Any],
    content_value: Dict[str, Any],
    emotion_info: Dict[str, Any],
) -> List[str]:
    """Determine content categories for the clip."""
    categories = []
    
    hook_type = hook_info.get("type", "general")
    if hook_type not in ("general",):
        categories.append(hook_type)
    
    value = content_value.get("value", "general")
    if value == "educational":
        categories.append("education")
    elif value == "actionable":
        categories.append("actionable")
    elif value == "unique_insight":
        categories.append("insight")
    
    emotion = emotion_info.get("primary", "neutral")
    if emotion not in ("neutral",):
        categories.append(emotion)
    
    # Always include at least one category
    if not categories:
        categories.append("general")
    
    return categories[:4]  # Max 4 categories