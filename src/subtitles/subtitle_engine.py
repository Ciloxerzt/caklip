#!/usr/bin/env python3
"""
Subtitle Generation Module - Real subtitle rendering
Implements word-level highlighting and configurable styles
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


class SubtitleLine:
    """Represents a single subtitle line with timing and styling."""
    
    def __init__(self, text: str, start: float, end: float,
                 word_highlights: Optional[List[Dict]] = None):
        self.text = text.strip()
        self.start = start
        self.end = end
        self.word_highlights = word_highlights or []
        self._duration = end - start
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "duration": self._duration,
            "word_highlights": self.word_highlights,
        }
    
    def get_middle_time(self) -> float:
        """Get the middle time of the subtitle."""
        return (self.start + self.end) / 2


class SubtitleEngine:
    """Handles subtitle generation and rendering."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            "font_size": 24,
            "font_color": "#FFFFFF",
            "background_color": "#00000080",
            "position": "bottom",  # bottom, top, margin
            "margin_percent": 5,
            "max_lines": 2,
            "chars_per_line": 40,
            "words_per_subtitle": None,
            "min_subtitle_duration": 1.0,
            "max_subtitle_duration": 6.0,
            "style": "clean",  # clean, bold, podcast, viral, karaoke
            "shadow": True,
            "stroke": True,
            "stroke_width": 2,
            "animation": False,
        }
    
    def generate_subtitles(self, segments: List[Dict[str, Any]],
                          words: Optional[List[Dict]] = None,
                          config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate subtitle lines from transcript segments and word data.
        
        Args:
            segments: Transcription segments with start/end/text
            words: Word-level timestamp data (optional)
            config: Subtitle styling configuration
            
        Returns:
            List of subtitle line dictionaries
        """
        config = config or self.config
        subtitles = []
        
        if not segments:
            return subtitles
        
        # If we have word-level data, use word-based grouping
        if words:
            generated = self._generate_word_based_subtitles(words, config)
        else:
            generated = self._generate_segment_based_subtitles(segments, config)
        
        # Apply style and rules
        for line in generated:
            # Enforce max lines rule
            if len(line["text"].split("\n")) > config.get("max_lines", 2):
                # Split into multiple lines
                split_lines = self._split_text(line["text"], config["chars_per_line"])
                for sl in split_lines:
                    subtitles.append(self._create_subtitle_line(sl, line.start, line.end, config))
            else:
                subtitles.append(self._create_subtitle_line(
                    line["text"], line.start, line.end, config))
        
        return subtitles
    
    def _split_text(self, text: str, chars_per_line: int) -> List[str]:
        """Split text into lines respecting character limits."""
        if not text:
            return []
        
        lines = []
        paragraphs = text.split("\n")
        
        for para in paragraphs:
            if not para.strip():
                continue
            
            # Split by sentences or by character limit
            sentences = para.split(". ")
            current_line = ""
            
            for sentence in sentences:
                test_line = current_line + ". " + sentence if current_line else sentence
                
                if len(test_line) <= chars_per_line:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line.rstrip(". "))
                    current_line = sentence
            
            if current_line:
                lines.append(current_line.rstrip(". "))
        
        return lines if lines else [text[:chars_per_line] or text]
    
    def _create_subtitle_line(self, text: str, start: float, end: float,
                               config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a subtitle line dictionary with styling."""
        # Enforce min/max duration
        duration = end - start
        duration = max(config.get("min_subtitle_duration", 1.0), 
                       min(duration, config.get("max_subtitle_duration", 6.0)))
        # Adjust end time to match duration
        adjusted_end = start + duration
        
        line_data = {
            "text": text,
            "start": round(start, 2),
            "end": round(adjusted_end, 2),
            "duration": round(duration, 2),
            "font_size": config.get("font_size", 24),
            "font_color": config.get("font_color", "#FFFFFF"),
            "background_color": config.get("background_color", "#00000080"),
            "position": config.get("position", "bottom"),
            "shadow": config.get("shadow", True),
            "stroke": config.get("stroke", True),
            "stroke_width": config.get("stroke_width", 2),
        }
        
        # Add style-specific properties
        style = config.get("style", "clean")
        if style == "bold":
            adjusted_end = start + duration
            line_data["font_weight"] = "bold"
        elif style == "podcast":
            # Podcast style: larger, simpler
            adjusted_end = start + duration
            line_data["font_size"] = config.get("font_size", 24) + 4
            line_data["font_color"] = "#E0E0E0"
            line_data["background_color"] = "none"
        elif style == "viral":
            # Viral style: animated, colorful
            adjusted_end = start + duration
            line_data["animation"] = True
            line_data["font_color"] = "#FF0000"
        elif style == "karaoke":
            # Karaoke style: word-by-word highlighting
            adjusted_end = start + duration
            # We'll add word highlighting info separately
        
        return adjusted_end, line_data
    
    def _generate_word_based_subtitles(self, words: List[Dict],
                                        config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate subtitles from word-level data."""
        subtitles = []
        
        # Group words into subtitle events
        if not words:
            return subtitles
        
        # Simple approach: group words into chunks based on timing
        # and config constraints
        
        # Group by time clusters
        if not words:
            return subtitles
        
        # Sort by start time
        sorted_words = sorted(words, key=lambda w: w.get("start", 0))
        
        # Create subtitle events every few seconds or when speaker changes
        current_chunk = []
        current_start = sorted_words[0].get("start", 0)
        
        for word_data in sorted_words:
            word = word_data.get("word", "")
            w_start = word_data.get("start", 0)
            w_end = word_data.get("end", 0)
            
            # Check if we should start a new subtitle
            time_since_start = w_start - current_start
            
            if (current_chunk and 
                time_since_start > config.get("max_subtitle_duration", 6.0)):
                # Create subtitle from current chunk
                subtitle = self._create_chunk_subtitle(current_chunk, current_start, w_end, config)
                if subtitle:
                    subtitles.append(subtitle)
                
                # Start new chunk
                current_chunk = []
                current_start = w_start
            
            current_chunk.append(word_data)
        
        # Don't forget the last chunk
        if current_chunk:
            subtitle = self._create_chunk_subtitle(current_chunk, current_start, 
                                                    sorted_words[-1].get("end", 0), config)
            if subtitle:
                subtitles.append(subtitle)
        
        return subtitles
    
    def _create_chunk_subtitle(self, words: List[Dict], start: float, end: float,
                                  config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a subtitle from a chunk of words."""
        if not words:
            return None
        
        # Build text from words
        text_parts = [w.get("word", "") for w in words if w.get("word")]
        if not text_parts:
            return None
        
        text = " ".join(text_parts)
        
        # Enforce duration limits
        duration = end - start
        duration = max(config.get("min_subtitle_duration", 1.0),
                       min(duration, config.get("max_subtitle_duration", 6.0)))
        adjusted_end = start + duration
        
        # Build word highlights for karaoke-style
        word_highlights = []
        for w in words:
            wh = {
                "word": w.get("word", ""),
                "start": w.get("start", start),
                "end": w.get("end", end),
            }
            word_highlights.append(wh)
        
        return {
            "text": text[:config.get("chars_per_line", 40) * 2],  # Truncate if needed
            "start": round(start, 2),
            "end": round(adjusted_end, 2),
            "duration": round(duration, 2),
            "word_highlights": word_highlights,
            "font_size": config.get("font_size", 24),
            "font_color": config.get("font_color", "#FFFFFF"),
            "background_color": config.get("background_color", "#00000080"),
            "position": config.get("position", "bottom"),
        }
    
    def _generate_segment_based_subtitles(self, segments: List[Dict[str, Any]],
                                           config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate subtitles directly from transcript segments."""
        subtitles = []
        
        for seg in segments:
            text = seg.get("text", "").strip()
            if not text:
                continue
            
            start = float(seg.get("start", 0))
            end = float(seg.get("end", 0))
            
            if end <= start:
                continue
            
            # Enforce duration limits
            duration = end - start
            duration = max(config.get("min_subtitle_duration", 1.0),
                           min(duration, config.get("max_subtitle_duration", 6.0)))
            adjusted_end = start + duration
            
            # Truncate text if too long
            chars_per_line = config.get("chars_per_line", 40)
            max_chars = chars_per_line * config.get("max_lines", 2)
            
            if len(text) > max_chars:
                # Truncate and add ellipsis
                text = text[:max_chars - 3] + "..."
            
            subtitle = {
                "text": text,
                "start": round(start, 2),
                "end": round(adjusted_end, 2),
                "duration": round(duration, 2),
                "font_size": config.get("font_size", 24),
                "font_color": config.get("font_color", "#FFFFFF"),
                "background_color": config.get("background_color", "#00000080"),
                "position": config.get("position", "bottom"),
            }
            
            subtitles.append(subtitle)
        
        return subtitles