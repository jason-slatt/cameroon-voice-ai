"""
Application constants - centralized to avoid magic strings/numbers
"""
from enum import Enum

# Audio Configuration
SAMPLE_RATE = 16000
MAX_AUDIO_SIZE_MB = 25
SUPPORTED_AUDIO_FORMATS = {"mp3", "wav", "ogg", "m4a", "opus"}

# Language Configuration
class CameroonLanguage(str, Enum):
    BAMEKA = "bameka"
    MEDUMBA = "medumba"
    YEMBA = "yemba"
    NGIEMBOON = "ngiemboon"
    FEFE = "fefe"
    BAMILEKE = "bamileke"
    FRENCH = "french"
    ENGLISH = "english"
    PIDGIN = "pidgin"

DEFAULT_LANGUAGE = CameroonLanguage.FRENCH

# Model Configuration
WHISPER_MODEL_NAME = "whisper-large-v3-cameroon"
LLAMA_MODEL_NAME = "llama-4-cameroon"
TTS_MODEL_NAME = "coqui-tts-cameroon"

# API Limits
MAX_TRANSCRIPTION_LENGTH_SECONDS = 300
MAX_CHAT_HISTORY_MESSAGES = 50
MAX_TTS_TEXT_LENGTH = 1000

# Processing Timeouts
TRANSCRIPTION_TIMEOUT_SECONDS = 60
LLM_INFERENCE_TIMEOUT_SECONDS = 30
TTS_GENERATION_TIMEOUT_SECONDS = 45
MAX_AUDIO_DURATION_SECONDS = 30  # or 45, up to you


# Response Templates
ERROR_AUDIO_TOO_LARGE = "Audio file exceeds maximum size of {max_size}MB"
ERROR_UNSUPPORTED_FORMAT = "Unsupported audio format. Supported: {formats}"
ERROR_TRANSCRIPTION_FAILED = "Transcription failed. Please try again."