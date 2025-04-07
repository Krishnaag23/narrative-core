"""
Defines the model for a detailed Character Profile,
including static traits, dynamic states, and relationships.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime

from ..input_processing.story_elements import CharacterInput, CharacterRole

class CharacterState(BaseModel):
    """Represents the dynamic state of a character at a point in time."""
    current_mood: Optional[str] = Field(None, description="Dominant emotion (e.g., 'anxious', 'elated'). Updated frequently.")
    short_term_goal: Optional[str] = Field(None, description="Immediate objective driving actions.")
    physical_condition: str = Field("Normal", description="e.g., 'Injured', 'Tired', 'Normal'.")
    last_significant_event_summary: Optional[str] = Field(None, description="Brief summary of the last major thing affecting them.")
    last_updated: datetime = Field(default_factory=datetime.now)

class CharacterProfile(BaseModel):
    """
    Comprehensive profile for a story character, combining initial input,
    generated details, and dynamic state.
    """
    character_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the character.")
    name: str = Field(..., description="Character's name.")
    role: CharacterRole = Field(..., description="Primary role (Protagonist, Antagonist, etc.).") 

    # --- Core Identity & Background (Relatively Static) ---
    backstory: str = Field(..., description="Detailed background and history generated by CharacterGenesis.")
    core_traits: List[str] = Field(default_factory=list, description="Fundamental personality traits (e.g., 'Brave', 'Cynical', 'Loyal').")
    motivations: List[str] = Field(default_factory=list, description="Underlying drives and desires.")
    flaws: List[str] = Field(default_factory=list, description="Significant weaknesses or shortcomings.")
    strengths: List[str] = Field(default_factory=list, description="Key abilities or positive attributes.")
    goals: List[str] = Field(default_factory=list, description="Long-term objectives the character is pursuing.")

    # --- Appearance & Voice (Descriptive) ---
    physical_description: str = Field("Not specified", description="Detailed physical appearance.")
    mannerisms: List[str] = Field(default_factory=list, description="Distinctive habits or gestures (e.g., 'Taps fingers when thinking').")
    voice_description: str = Field("Not specified", description="Tone, pitch, accent, common phrases.")

    # --- Dynamic Elements ---
    current_state: CharacterState = Field(default_factory=CharacterState)
    # Relationships are handled by RelationshipManager, but we might store a cache here
    # relationships: Dict[str, str] = Field(default_factory=dict, description="Cache of relationship status with other character IDs.")

    # --- Metadata ---
    initial_input: CharacterInput = Field(..., description="The original input data used for genesis.")
    created_at: datetime = Field(default_factory=datetime.now)
    last_profile_update: datetime = Field(default_factory=datetime.now)

    def update_state(self, updates: Dict[str, Any]):
        """Updates the character's dynamic state."""
        now = datetime.now()
        for key, value in updates.items():
            if hasattr(self.current_state, key):
                setattr(self.current_state, key, value)
        self.current_state.last_updated = now
        self.last_profile_update = now
        print(f"DEBUG: Updated state for {self.name}: {updates}") # Debug logging

    def get_core_summary(self) -> str:
        """Provides a concise summary of the character for LLM prompts."""
        summary = (
            f"Name: {self.name}\n"
            f"Role: {self.role}\n"
            f"Core Traits: {', '.join(self.core_traits)}\n"
            f"Motivations: {', '.join(self.motivations)}\n"
            f"Current Goals: {', '.join(self.goals)}\n"
            f"Flaws: {', '.join(self.flaws)}\n"
            f"Voice: {self.voice_description}\n"
            f"Backstory Summary: {self.backstory[:200]}...\n" # Truncate backstory
            f"Current Mood: {self.current_state.current_mood or 'Neutral'}\n"
            f"Short-term Goal: {self.current_state.short_term_goal or 'None apparent'}"
        )
        return summary

    class Config:
        validate_assignment = True 