#!/usr/bin/env python3
"""
Transcription Module - Provider abstraction layer
Supports local and remote transcription providers
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class TranscriptionResult:
    """Standardized transcription output format."""
    
    def __init__(self):
        self.text: str = ""
        self.full_text: str = ""
        self.confidence: float = 0.0
        self.segments: List[Dict[str, Any]] = []
        self.words: List[Dict[str, Any]] = []
        self.provider: str = ""
        self.model: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "full_text": self.full_text,
            "confidence": self.confidence,
            "segments": [{"start": s.get("start"), "end": s.get("end"), "text": s.get("text", "")} 
                        for s in self.segments],
            "words": self.words,
            "provider": self.provider,
            "model": self.model,
        }


class BaseTranscriptionProvider:
    """Abstract base class for transcription providers."""
    
    def transcribe(self, audio_path: Path, **kwargs) -> TranscriptionResult:
        raise NotImplementedError("Subclasses must implement transcribe()")
    
    def get_word_timestamps(self) -> bool:
        """Whether this provider supports word-level timestamps."""
        return False
    
    def get_provider_name(self) -> str:
        return self.__class__.__name__


class LocalWhisperProvider(BaseTranscriptionProvider):
    """Local Whisper model transcription."""
    
    def __init__(self, model_size: str = "base", language: Optional[str] = None):
        self.model_size = model_size
        self.language = language
        self.model = None
        self._model_loaded = False
    
    def _ensure_model(self):
        """Load Whisper model if not already loaded."""
        if not self._model_loaded:
            try:
                import whisper
                self.model = whisper.load_model(self.model_size)
                self._model_loaded = True
            except ImportError:
                print("WARNING: whisper not installed, falling back to subprocess", file=sys.stderr)
    
    def transcribe(self, audio_path: Path, **kwargs) -> TranscriptionResult:
        result = TranscriptionResult()
        result.provider = self.get_provider_name()
        result.model = self.model_size
        
        self._ensure_model()
        
        if self.model:
            try:
                audio = str(audio_path.resolve())
                transcribe_result = self.model.transcribe(
                    audio,
                    language=self.language,
                    **kwargs
                )
                
                result.text = transcribe_result.get("text", "")
                result.full_text = result.text
                result.confidence = transcribe_result.get("language_probability", 1.0)
                
                # Extract segments
                result.segments = transcribe_result.get("segments", [])
                
                # Extract words if available
                if "words" in transcribe_result and transcribe_result["words"]:
                    result.words = transcribe_result["words"]
                elif self._has_word_level_timestamps():
                    # Build words from segments
                    result.words = self._build_words_from_segments()
                
                return result
            except Exception as e:
                print(f"Whisper transcription error: {e}", file=sys.stderr)
                return result
        else:
            # Fallback to ffmpeg/ffprobe-based approach
            return self._ffmpeg_fallback(audio_path)
    
    def _has_word_level_timestamps(self) -> bool:
        """Check if segments have word-level data."""
        if not self.segments:
            return False
        return any("words" in s and s["words"] for s in self.segments[:1])
    
    def _build_words_from_segments(self) -> List[Dict[str, Any]]:
        """Build word list from segment-level data."""
        words = []
        for segment in self.segments:
            segment_words = segment.get("words", [])
            for w in segment_words:
                words.append({
                    "word": w.get("word", ""),
                    "start": w.get("start", segment.get("start", 0)),
                    "end": w.get("end", segment.get("end", 0)),
                    "confidence": w.get("confidence", 1.0),
                })
        return words
    
    def _ffmpeg_fallback(self, audio_path: Path) -> TranscriptionResult:
        """Fallback using basic audio analysis."""
        result = TranscriptionResult()
        result.provider = self.get_provider_name()
        result.text = "[Fallback: Whisper model not available or failed]"
        return result
    
    def get_provider_name(self) -> str:
        return f"whisper-{self.model_size}"


class RemoteAPIProvider(BaseTranscriptionProvider):
    """Remote transcription API provider."""
    
    def __init__(self, api_key: str, base_url: str = "", 
                 model: str = "whisper-1", provider_name: str = "openai"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.provider_name = provider_name
    
    def transcribe(self, audio_path: Path, **kwargs) -> TranscriptionResult:
        result = TranscriptionResult()
        result.provider = self.provider_name
        result.model = self.model
        
        # Determine the API endpoint
        if self.base_url:
            endpoint = f"{self.base_url}/v1/audio/transcriptions"
        else:
            endpoint = f"https://api.openai.com/v1/audio/transcriptions"
        
        # Prepare the request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        
        # Try to use curl for the API call
        try:
            audio_file = str(audio_path.resolve())
            
            # Build curl command
            curl_cmd = [
                "curl", "-s", "-X", "POST",
                "-H", f"Authorization: Bearer {self.api_key}",
                "-H", "Content-Type: multipart/form-data",
                "-F", f"file=@{audio_file}",
                "-F", f"model={self.model}",
                endpoint
            ]
            
            proc = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=120)
            
            if proc.returncode != 0:
                result.text = f"[curl error: {proc.stderr}]"
                return result
            
            # Parse response
            try:
                resp_data = json.loads(proc.stdout)
                result.text = resp_data.get("text", "").strip()
                result.full_text = result.text
                result.confidence = resp_data.get("confidence", 1.0)
                result.segments = resp_data.get("segments", [])
                result.words = resp_data.get("words", [])
                return result
            except json.JSONDecodeError:
                result.text = proc.stdout[:200]
                return result
                
        except Exception as e:
            result.text = f"[ transcription error: {str(e)} ]"
            return result
    
    def get_word_timestamps(self) -> bool:
        """Remote APIs typically support word timestamps."""
        return True
    
    def get_provider_name(self) -> str:
        return f"{self.provider_name}-api"


def create_provider(provider_type: str, **kwargs) -> BaseTranscriptionProvider:
    """Factory function to create transcription providers."""
    if provider_type == "local-whisper":
        model_size = kwargs.get("model_size", "base")
        language = kwargs.get("language")
        return LocalWhisperProvider(model_size=model_size, language=language)
    elif provider_type == "remote-api":
        api_key = kwargs.get("api_key", "")
        base_url = kwargs.get("base_url", "")
        model = kwargs.get("model", "whisper-1")
        provider_name = kwargs.get("provider_name", "openai")
        return RemoteAPIProvider(api_key=api_key, base_url=base_url,
                                 model=model, provider_name=provider_name)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")