#!/usr/bin/env python3
"""
AI Analysis Module - Semantic analysis for clip detection
Uses AI only for: semantic analysis, hook detection, interesting moment detection,
clip descriptions, title generation, caption generation
Never used for: deterministic video processing, FFmpeg operations, subtitle rendering
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Structured JSON schema for AI clip detection output
CLIP_DETECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "clips": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Clip start timestamp in seconds"
                    },
                    "end": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Clip end timestamp in seconds"
                    },
                    "hook": {
                        "type": "string",
                        "max_length": 200,
                        "description": "Hook description or opening statement"
                    },
                    "reason": {
                        "type": "string",
                        "max_length": 500,
                        "description": "Why this segment was selected"
                    },
                    "score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Clip potential score (0-100)"
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Content categories (hook, education, emotion, curiosity, value, other)"
                    },
                    "transcript_excerpt": {
                        "type": "string",
                        "max_length": 300,
                        "description": "Short transcript excerpt"
                    }
                },
                "required": ["start", "end", "hook", "reason", "score", "categories"],
                "additionalProperties": False
            },
            "description": "List of detected clips"
        }
    },
    "required": ["clips"],
    "additionalProperties": False
}


def validate_clip_detection_output(data: Any) -> Tuple[bool, Optional[Dict]]:
    """Validate AI output against the clip detection schema.

    Returns (is_valid, validated_data_or_None).
    """
    if not isinstance(data, dict):
        return False, None

    if "clips" not in data:
        return False, None

    clips = data.get("clips", [])
    if not isinstance(clips, list):
        return False, None

    validated_clips = []
    for i, clip in enumerate(clips):
        if not isinstance(clip, dict):
            continue  # Skip invalid clip entries

        # Validate required fields
        required_fields = ["start", "end", "hook", "reason", "score", "categories"]
        if not all(f in clip for f in required_fields):
            continue

        # Clamp values
        try:
            start = max(0, min(float(clip["start"]), 1000000))
            end = max(0, min(float(clip["end"]), 1000000))
            if end <= start:
                continue  # Invalid: end must be after start

            score = max(0, min(int(clip["score"]), 100))
            categories = clip.get("categories", [])
            if not isinstance(categories, list):
                categories = []

            hook = str(clip["hook"])[:200]
            reason = str(clip["reason"])[:500]

            validated_clips.append({
                "start": start,
                "end": end,
                "hook": hook,
                "reason": reason,
                "score": score,
                "categories": categories,
                "transcript_excerpt": str(clip.get("transcript_excerpt", ""))[:300]
            })
        except (ValueError, TypeError):
            continue

    if not validated_clips:
        return False, None

    return True, {"clips": validated_clips}


def detect_hook_type(transcript_text: str, start: float, end: float) -> Dict[str, Any]:
    """Detect hook type from transcript segment.

    Deterministic analysis - no AI used.
    """
    if not transcript_text:
        return {"type": "unknown", "strength": 0}

    segment_text = transcript_text

    # Detect hook patterns
    hook_score = 0
    hook_type = "unknown"

    # Question hook
    if segment_text.strip().endswith("?"):
        hook_type = "question"
        hook_score += 20

    # Strong opinion
    opinion_words = ["sangat", "must", "terkadang", "rasa", "salah", "betul"]
    if any(w in segment_text.lower() for w in opinion_words):
        if hook_type == "unknown":
            hook_type = "opinion"
        hook_score += 15

    # Surprising statement
    surprise_words = ["wajar", "luar", "tidak", "gapapa", "luar biasa"]
    if any(w in segment_text.lower() for w in surprise_words):
        if hook_type == "unknown":
            hook_type = "surprising"
        hook_score += 15

    # Emotional moment
    emotion_words = ["sedih", "bahagia", "marah", "terlena", "sialan"]
    if any(w in segment_text.lower() for w in emotion_words):
        if hook_type == "unknown":
            hook_type = "emotional"
        hook_score += 10

    # Curiosity gap
    curiosity_words = ["tahu", "mengapa", "bagaimana", "rahasia", "fakta"]
    if any(w in segment_text.lower() for w in curiosity_words):
        if hook_type == "unknown":
            hook_type = "curiosity"
        hook_score += 10

    # Punchline
    punchline_words = ["jadi", "maka", "oleh", "akibat", "terjadi"]
    if any(w in segment_text.lower() for w in punchline_words):
        if hook_type == "unknown":
            hook_type = "punchline"
        hook_score += 5

    # If no specific pattern detected, it's general content
    if hook_type == "unknown":
        hook_type = "general"

    strength = min(hook_score, 100)

    return {"type": hook_type, "strength": strength}


def analyze_content_value(transcript_text: str) -> Dict[str, Any]:
    """Analyze educational/informational value of content.

    Deterministic analysis based on keyword patterns.
    """
    if not transcript_text:
        return {"value": "none", "confidence": 0}

    text_lower = transcript_text.lower()

    educational_keywords = [
        "sebenarnya", "mengapa", "cara", "tutorial", "pembelajaran",
        "penjelasan", "konsep", "prinsip", "teori", "fundamental"
    ]

    actionable_keywords = [
        "coba", "lakukan", "buat", "mulailah", "trigger", "langkah",
        "validasi", "ujicoba", "proses"
    ]

    unique_insight_keywords = [
        "singkat", "wawasan", "perspektif", "unik", "menginginkan",
        "lihat", "beda", "perbedaan", "insight"
    ]

    comparison_keywords = [
        "kayak", "seperti", "berbeda", "dibanding", "versus",
        "kayaknya", "mirip"
    ]

    educational_count = sum(1 for k in educational_keywords if k in text_lower)
    actionable_count = sum(1 for k in actionable_keywords if k in text_lower)
    unique_insight_count = sum(1 for k in unique_insight_keywords if k in text_lower)
    comparison_count = sum(1 for k in comparison_keywords if k in text_lower)

    total_keywords = educational_count + actionable_count + unique_insight_count + comparison_count
    confidence = min(total_keywords / 5.0, 1.0)

    if educational_count >= 2:
        value = "educational"
    elif actionable_count >= 2:
        value = "actionable"
    elif unique_insight_count >= 2:
        value = "unique_insight"
    elif comparison_count >= 2:
        value = "comparison"
    elif total_keywords >= 1:
        value = "informational"
    else:
        value = "general"

    return {"value": value, "confidence": confidence}


def analyze_emotion_indicators(transcript_text: str) -> Dict[str, Any]:
    """Analyze emotional intensity indicators."""
    if not transcript_text:
        return {"primary": "neutral", "intensity": 0}

    text_lower = transcript_text.lower()

    emotion_categories = {
        "excitement": ["seru", "gapay", "wow", "keren", "kagum", "kaget"],
        "surprise": ["luar", "wajar", "kaget", "tiba-tiba", "tiba2"],
        "humor": ["segal", "anjing", "lagi", "aja", "joke", "haha"],
        "tension": ["stres", "tekanan", "kacau", "masalah", "galat"],
        "inspiration": ["menginspirasi", "berpihak", "semangat", "semangat"],
        "sadness": ["sedih", "duka", "sakit", "rasa", "hampa"],
    }

    detected = []
    for emotion, keywords in emotion_categories.items():
        if any(k in text_lower for k in keywords):
            detected.append(emotion)

    if not detected:
        primary = "neutral"
        intensity = 0
    else:
        primary = detected[0]
        # Rough intensity based on keyword density
        intensity = min(len(detected) / 3.0 * 50, 50)

    return {"primary": primary, "intensity": round(intensity, 1)}


def compute_clip_score_deterministic(
    hook_info: Dict[str, Any],
    content_value: Dict[str, Any],
    emotion_info: Dict[str, Any],
    silence_ratio: float,
    speech_density: float,
    clip_duration: float,
    min_duration: float = 10,
    max_duration: float = 60
) -> Dict[str, Any]:
    """Compute clip score using deterministic weights.

    Weights (percentages):
    Hook strength: 25%
    Information value: 20%
    Emotional impact: 15%
    Curiosity: 15%
    Standalone context: 10%
    Clarity: 10%
    Audio quality: 5% (silence/speech ratio)
    Total: 100%
    """

    # Hook strength component (25%)
    hook_score = hook_info.get("strength", 0)
    hook_component = (hook_score / 100) * 25

    # Information value component (20%)
    value = content_value.get("value", "general")
    value_map = {"educational": 100, "actionable": 100, "unique_insight": 100,
                 "informational": 70, "general": 30, "none": 0}
    value_component = (value_map.get(value, 30) / 100) * 20

    # Emotional impact component (15%)
    emotion = emotion_info.get("primary", "neutral")
    emotion_map = {"excitement": 100, "surprise": 90, "humor": 80,
                   "tension": 70, "inspiration": 85, "sadness": 60, "neutral": 20}
    emotion_component = (emotion_map.get(emotion, 20) / 100) * 15

    # Curiosity component (15%) - based on presence of question words
    text = hook_info.get("reason", "")
    curiosity_words = ["bagaimana", "mengapa", "tahu", "rahasia", "kapan", "di"]
    curiosity_count = sum(1 for w in curiosity_words if w in text.lower())
    curiosity_component = min(curiosity_count * 15 / 3, 15)  # max 15

    # Standalone context component (10%)
    # Clip should make sense on its own - check if hook provides enough context
    hook_reason = hook_info.get("reason", "")
    context_score = 50 if len(hook_reason) > 20 else 20  # Simple heuristic
    context_component = (context_score / 100) * 10

    # Clarity component (10%) - based on speech density and silence
    clarity_adjuster = (speech_density * 0.6 + (1 - silence_ratio) * 0.4)
    clarity_component = (clarity_adjuster / 1) * 10  # Normalized to 0-10

    # Audio quality component (5%) - based on silence/speech ratio
    audio_quality = max(0, 100 - (silence_ratio * 100))  # Less silence = better
    audio_component = (audio_quality / 100) * 5

    # Total score
    total = round(hook_component + value_component + emotion_component +
                  curiosity_component + context_component + clarity_component + audio_component)

    return {
        "score": max(0, min(total, 100)),
        "breakdown": {
            "hook": round(hook_component),
            "information": round(value_component),
            "emotion": round(emotion_component),
            "curiosity": round(curiosity_component),
            "context": round(context_component),
            "clarity": round(clarity_component),
            "audio": round(audio_component)
        }
    }


def ai_enhanced_clip_detection(
    transcript: Dict[str, Any],
    api_key: str,
    base_url: str = "",
    model: str = "gpt-4o-mini"
) -> Optional[Dict[str, Any]]:
    """Use AI for enhanced clip detection (optional).

    Only used when AI is explicitly enabled. The AI provides semantic analysis
    and hook detection, but the final clip timestamps and scoring are always
    validated by deterministic systems.

    Returns None if AI is unavailable or fails (falls back to deterministic).
    """
    try:
        import urllib.request
        import urllib.error

        # Build the AI request endpoint
        if base_url:
            endpoint = f"{base_url}/v1/chat/completions"
        else:
            endpoint = "https://api.openai.com/v1/chat/completions"

        # Construct the AI prompt for clip detection
        # Use the first few segments as context
        segments = transcript.get("segments", [])
        if not segments:
            return None

        # Prepare context from first few segments
        context_parts = []
        for i, seg in enumerate(segments[:5]):
            text = seg.get("text", "").strip()
            if text:
                # Truncate long segments
                if len(text) > 200:
                    text = text[:200] + "..."
                context_parts.append(f"[{seg.get('start', i)}-{seg.get('end', i+1)}]: {text}")

        context = "\n".join(context_parts) if context_parts else "No transcript available"

        # Build the prompt
        prompt = "Analyze the following transcript segments and identify the most interesting moments for short-form video clipping.\n\n" \
                 "CONTEXT TRANSCRIPT:\n" + context + "\n\n" \
                 "TASK: Identify 3-5 optimal clip segments. For each clip, provide:\n" \
                 "1. start and end timestamps (in seconds from the beginning)\n" \
                 "2. A hook description (the most interesting opening statement)\n" \
                 "3. A reason why this segment is interesting\n" \
                 "4. A score from 0-100 representing the clip's potential for virality/engagement\n" \
                 "5. Categories: hook, education, emotion, curiosity, value, or other\n\n" \
                 "IMPORTANT GUIDELINES:\n" \
                 "- Clips should make sense when viewed alone (standalone context)\n" \
                 "- Avoid clips that begin or end mid-sentence unless necessary\n" \
                 "- Prefer clips with HOOK + DEVELOPMENT + PAYOFF structure\n" \
                 "- Include enough surrounding context for the clip to be understandable\n" \
                 "- Score should be realistic (0-100), not inflated\n" \
                 "- Diversity: include different types of moments (humor, education, emotion, etc.)\n\n" \
                 "RESPONSE FORMAT: Strict JSON only, no prose, no explanations:\n" \
                 "{ \"clips\": [\n" \
                 "    { \"start\": 123.4, \"end\": 157.8, \"hook\": \"Opening statement\",\n" \
                 "      \"reason\": \"Why this segment is interesting\",\n" \
                 "      \"score\": 87, \"categories\": [\"hook\", \"education\", \"curiosity\"] }\n" \
                 "  ]\n" \
                 "}\n\n" \
                 "CRITICAL: Output MUST be valid JSON. No surrounding text, no prose. " \
                 "The JSON must parse successfully. Do not include any text before or after the JSON."

        # Prepare the message
        messages = [
            {"role": "system", "content": "You are an expert video clip analyst. Your job is to identify the most engaging moments from transcript text for short-form video content. Always output strict JSON as specified. Never add prose or explanations outside the JSON."},
            {"role": "user", "content": prompt}
        ]

        # Build curl command
        curl_cmd = [
            "curl", "-s", "-X", "POST",
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {api_key}",
            "-d", json.dumps({"messages": messages, "model": model, "temperature": 0.3}),
            endpoint
        ]

        proc = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)

        if proc.returncode != 0:
            print(f"AI API error: {proc.stderr[:200]}", file=sys.stderr)
            return None

        # Parse response
        response_text = proc.stdout.strip()

        # Try to extract JSON from response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            print("No JSON found in AI response", file=sys.stderr)
            return None

        json_str = response_text[json_start:json_end]

        try:
            ai_data = json.loads(json_str)
        except json.JSONDecodeError:
            print(f"Failed to parse AI JSON: {json_str[:200]}", file=sys.stderr)
            return None

        # Validate against schema
        is_valid, validated = validate_clip_detection_output(ai_data)

        if not is_valid:
            print("AI output failed schema validation", file=sys.stderr)
            # Try limited repair
            if validated is None:
                return None  # Can't repair, fall back to deterministic

        return validated

    except ImportError:
        print("urllib not available, skipping AI enhancement", file=sys.stderr)
        return None
    except Exception as e:
        print(f"AI enhancement error: {e}", file=sys.stderr)
        return None