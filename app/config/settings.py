from pydantic import BaseSettings, AnyHttpUrl
import os


class Settings(BaseSettings):
    # LLM: OpenAI-compatible (OpenAI, Ollama, etc.)
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "ollama")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.1")

    # Whisper STT model (English-only, as requested)
    WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL_NAME", "base.en")

    # Coqui TTS model
    TTS_MODEL_NAME: str = os.getenv(
        "TTS_MODEL_NAME", "tts_models/en/ljspeech/tacotron2-DDC_ph"
    )

    # Storage for generated audio
    AUDIO_STORAGE_PATH: str = os.getenv("AUDIO_STORAGE_PATH", "data/audio")

    # BAFOKA / backend API
    BACKEND_BASE_URL: AnyHttpUrl = "https://sandbox.bafoka.network"
    BACKEND_API_KEY: str | None = os.getenv("BACKEND_API_KEY")
    BACKEND_TIMEOUT: int = int(os.getenv("BACKEND_TIMEOUT", "10"))

    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    class Config:
        env_file = ".env"


settings = Settings()