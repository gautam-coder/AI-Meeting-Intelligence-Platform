from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices
from typing import Optional
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "AI Meeting Intelligence"
    environment: str = Field(default="dev")
    data_dir: str = Field(default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))

    # File upload
    max_upload_mb: int = 1024  # 1GB default
    allowed_extensions: set[str] = {"mp3", "mp4", "wav", "m4a", "aac", "flac", "webm", "ogg"}

    # Whisper.cpp
    whisper_binary_path: str = Field(
        default="./bin/whisper",
        validation_alias=AliasChoices("WHISPER_BIN", "whisper_bin", "WHISPER_BINARY_PATH"),
    )
    whisper_model_path: str = Field(
        default="./models/ggml-base.en.bin",
        validation_alias=AliasChoices("WHISPER_MODEL", "whisper_model", "WHISPER_MODEL_PATH"),
    )
    whisper_model_url: Optional[str] = Field(
        default=os.environ.get(
            "WHISPER_MODEL_URL",
            # Default HF mirror commonly used for ggml models
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
        ),
        validation_alias=AliasChoices("WHISPER_MODEL_URL", "whisper_model_url"),
    )
    whisper_bin_url: Optional[str] = Field(
        default=os.environ.get("WHISPER_BIN_URL"),
        validation_alias=AliasChoices("WHISPER_BIN_URL", "whisper_bin_url"),
    )
    whisper_language: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("WHISPER_LANGUAGE", "whisper_language"),
    )  # auto-detect if None
    whisper_diarize: bool = Field(
        default=True,
        validation_alias=AliasChoices("WHISPER_DIARIZE", "whisper_diarize"),
    )  # tinydiarize
    whisper_threads: int = Field(
        default=8,
        validation_alias=AliasChoices("WHISPER_THREADS", "whisper_threads"),
    )
    whisper_gpu_layers: int = Field(
        default=0,
        validation_alias=AliasChoices("WHISPER_GPU_LAYERS", "whisper_gpu_layers"),
    )  # set >0 for metal/cuda builds

    # Transcription engine
    transcription_engine: str = Field(
        default=os.environ.get("TRANSCRIPTION_ENGINE", "faster_whisper"),  # whisper_cpp | faster_whisper
        validation_alias=AliasChoices("TRANSCRIPTION_ENGINE", "transcription_engine"),
    )

    # faster-whisper
    faster_whisper_model: str = Field(
        default=os.environ.get("FASTER_WHISPER_MODEL", "base"),
        validation_alias=AliasChoices("FASTER_WHISPER_MODEL", "faster_whisper_model"),
    )
    faster_whisper_compute_type: str = Field(
        default=os.environ.get("FASTER_WHISPER_COMPUTE", "int8"),  # float16 on GPUs, int8 on CPU
        validation_alias=AliasChoices("FASTER_WHISPER_COMPUTE", "faster_whisper_compute_type"),
    )

    # Diarization (pyannote)
    diarization_enabled: bool = Field(
        default=bool(int(os.environ.get("DIARIZATION_ENABLED", "0"))),
        validation_alias=AliasChoices("DIARIZATION_ENABLED", "diarization_enabled"),
    )
    pyannote_pipeline: str = Field(
        default=os.environ.get("PYANNOTE_PIPELINE", "pyannote/speaker-diarization-3.1"),
        validation_alias=AliasChoices("PYANNOTE_PIPELINE", "pyannote_pipeline"),
    )
    hf_token: Optional[str] = Field(
        default=os.environ.get("HF_TOKEN"),
        validation_alias=AliasChoices("HF_TOKEN", "huggingface_token"),
    )

    # Ollama
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "ollama_base_url"),
    )
    ollama_chat_model: str = Field(
        default="llama3.2",
        validation_alias=AliasChoices("OLLAMA_CHAT_MODEL", "ollama_chat_model"),
    )
    ollama_summarize_model: str = Field(
        default="llama3.2",
        validation_alias=AliasChoices(
            "OLLAMA_SUMMARY_MODEL",
            "ollama_summary_model",
            "OLLAMA_SUMMARIZE_MODEL",
            "ollama_summarize_model",
        ),
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        validation_alias=AliasChoices(
            "OLLAMA_EMBED_MODEL",
            "ollama_embed_model",
            "OLLAMA_EMBEDDING_MODEL",
            "ollama_embedding_model",
        ),
    )
    ollama_timeout_seconds: int = Field(
        default=120,
        validation_alias=AliasChoices("OLLAMA_TIMEOUT_SECONDS", "ollama_timeout_seconds"),
    )

    # ChromaDB
    chroma_persist_dir: str = Field(default_factory=lambda: os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma"))
    chroma_collection_name: str = "meeting_segments"

    # DB
    sqlite_path: str = Field(default_factory=lambda: os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db"))


settings = Settings()

# Ensure directories exist
os.makedirs(settings.data_dir, exist_ok=True)
os.makedirs(os.path.join(settings.data_dir, "uploads"), exist_ok=True)
os.makedirs(os.path.join(settings.data_dir, "artifacts"), exist_ok=True)
os.makedirs(settings.chroma_persist_dir, exist_ok=True)
