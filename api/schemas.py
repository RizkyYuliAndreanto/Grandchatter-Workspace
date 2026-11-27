"""Pydantic schemas for REST API."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Naskah teks untuk disintesis")
    voice: str = Field("sample_voice", description="Nama preset suara di prompt_audio/")
    profile: Optional[Literal["low_resource", "fast"]] = Field(None, description="Profil hardware: 'low_resource' atau 'fast'")
    temperature: float = Field(0.25, ge=0.1, le=1.0, description="Variasi intonasi")
    tempo: float = Field(1.0, ge=0.8, le=1.5, description="Kecepatan bicara")
    pitch: float = Field(0.0, ge=-4.0, le=4.0, description="Pitch semitone")


class VoicesResponse(BaseModel):
    voices: List[str]


class SegmentItem(BaseModel):
    id: str = Field(..., min_length=1, max_length=100, description="Identitas unik segmen (misal: 'scene_01')")
    text: str = Field(..., min_length=1, max_length=5000, description="Naskah teks segmen")
    tempo: Optional[float] = Field(None, ge=0.8, le=1.5, description="Tempo opsional per segmen")
    pitch: Optional[float] = Field(None, ge=-4.0, le=4.0, description="Pitch opsional per segmen")


class BatchRequest(BaseModel):
    voice: str = Field("sample_voice", description="Nama preset suara di prompt_audio/")
    profile: Optional[Literal["low_resource", "fast"]] = Field(None, description="Profil hardware")
    tempo: float = Field(1.0, ge=0.8, le=1.5, description="Default tempo jika segmen tidak menentukan")
    pitch: float = Field(0.0, ge=-4.0, le=4.0, description="Default pitch jika segmen tidak menentukan")
    temperature: float = Field(0.25, ge=0.1, le=1.0, description="Variasi intonasi")
    segments: List[SegmentItem] = Field(..., min_length=1, max_length=1000, description="Array naskah segmen (bisa ratusan)")


class SegmentResult(BaseModel):
    id: str
    audio_url: Optional[str] = None
    duration_s: float = 0.0
    status: str = "success"
    error: Optional[str] = None


class BatchResponse(BaseModel):
    status: str
    batch_id: str
    profile_used: str
    total_segments: int
    successful_segments: int
    failed_segments: int
    results: List[SegmentResult]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str
    default_profile: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
