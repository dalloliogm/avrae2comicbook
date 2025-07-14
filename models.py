"""Data models for the D&D Comic Book Generator."""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class EventType(str, Enum):
    """Types of events that can occur in a D&D session."""
    DIALOGUE = "dialogue"
    ACTION = "action"
    COMBAT = "combat"
    ROLL = "roll"
    NARRATION = "narration"
    SCENE_TRANSITION = "scene_transition"


class CharacterClass(str, Enum):
    """D&D character classes."""
    BARBARIAN = "barbarian"
    BARD = "bard"
    CLERIC = "cleric"
    DRUID = "druid"
    FIGHTER = "fighter"
    MONK = "monk"
    PALADIN = "paladin"
    RANGER = "ranger"
    ROGUE = "rogue"
    SORCERER = "sorcerer"
    WARLOCK = "warlock"
    WIZARD = "wizard"


class Character(BaseModel):
    """Character model for the knowledge graph."""
    id: str
    name: str
    player_name: Optional[str] = None
    race: Optional[str] = None
    character_class: Optional[CharacterClass] = None
    level: Optional[int] = None
    description: Optional[str] = None
    stats: Dict[str, Any] = Field(default_factory=dict)
    equipment: List[str] = Field(default_factory=list)
    spells: List[str] = Field(default_factory=list)
    relationships: Dict[str, str] = Field(default_factory=dict)
    image_references: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class Location(BaseModel):
    """Location model for the knowledge graph."""
    id: str
    name: str
    description: Optional[str] = None
    environment_type: Optional[str] = None  # indoor, outdoor, underwater, etc.
    atmosphere: Optional[str] = None  # dark, bright, mysterious, etc.
    key_features: List[str] = Field(default_factory=list)
    
    
class Event(BaseModel):
    """Event model for the knowledge graph."""
    id: str
    timestamp: datetime
    event_type: EventType
    description: str
    participants: List[str] = Field(default_factory=list)
    location_id: Optional[str] = None
    game_mechanics: Dict[str, Any] = Field(default_factory=dict)
    dialogue_content: Optional[str] = None
    speaker_id: Optional[str] = None
    target_id: Optional[str] = None
    
    class Config:
        use_enum_values = True


class Scene(BaseModel):
    """Scene model representing a sequence of related events."""
    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location_id: str
    events: List[str] = Field(default_factory=list)  # Event IDs
    main_characters: List[str] = Field(default_factory=list)  # Character IDs
    scene_type: str  # combat, dialogue, exploration, etc.
    dramatic_tension: float = Field(0.0, ge=0.0, le=1.0)  # 0-1 scale
    
    
class Panel(BaseModel):
    """Comic panel model."""
    id: str
    scene_id: str
    panel_number: int
    panel_type: str  # action, dialogue, environment, close_up
    description: str
    characters: List[str] = Field(default_factory=list)
    dialogue: Optional[str] = None
    narration: Optional[str] = None
    visual_prompt: Optional[str] = None
    generated_image_path: Optional[str] = None
    
    
class ComicPage(BaseModel):
    """Comic page model."""
    id: str
    mission_id: str
    page_number: int
    panels: List[Panel] = Field(default_factory=list)
    layout_type: str = "standard"  # standard, splash, grid
    generated_image_path: Optional[str] = None
    
    
class Mission(BaseModel):
    """Mission model representing a complete D&D session."""
    id: str
    title: str
    description: Optional[str] = None
    session_date: datetime
    characters: List[Character] = Field(default_factory=list)
    locations: List[Location] = Field(default_factory=list)
    events: List[Event] = Field(default_factory=list)
    scenes: List[Scene] = Field(default_factory=list)
    pages: List[ComicPage] = Field(default_factory=list)
    
    
class ProcessingStatus(BaseModel):
    """Status tracking for mission processing."""
    mission_id: str
    status: str  # parsing, planning, generating, reviewing, completed, failed
    progress: float = Field(0.0, ge=0.0, le=1.0)
    current_step: str
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    
class ImageGenerationRequest(BaseModel):
    """Request model for image generation."""
    id: str
    prompt: str
    style: str = "comic book art"
    size: str = "1024x1024"
    quality: str = "standard"
    panel_id: Optional[str] = None
    page_id: Optional[str] = None
    priority: int = 1
    
    
class ImageGenerationResult(BaseModel):
    """Result model for image generation."""
    request_id: str
    success: bool
    image_path: Optional[str] = None
    error_message: Optional[str] = None
    generation_time: float
    api_used: str
    quality_score: Optional[float] = None