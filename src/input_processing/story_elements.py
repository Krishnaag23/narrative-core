
"""
Defines data models for structuring the story elements gathered
during the input processing phase. These models ensure data validation
and provide a clear contract for downstream modules.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, field_validator

# --- Enums ---

class StoryLength(Enum):
    SHORT = "Short (1-3 episodes)"
    MEDIUM = "Medium (4-10 episodes)"
    LONG = "Long (10+ episodes)"

class TargetAudience(Enum):
    CHILDREN = "Children"
    YOUNG_ADULTS = "Young Adults"
    ADULTS = "Adults"
    ALL_AGES = "All Ages"

class CharacterRole(Enum):
    PROTAGONIST = "Protagonist"
    ANTAGONIST = "Antagonist"
    SUPPORTING = "Supporting"
    MENTOR = "Mentor"
    FOIL = "Foil"
    OTHER = "Other"

class ConflictType(Enum):
    PERSON_VS_PERSON = "person_vs_person"
    PERSON_VS_NATURE = "person_vs_nature"
    PERSON_VS_SOCIETY = "person_vs_society"
    PERSON_VS_SELF = "person_vs_self"
    PERSON_VS_TECHNOLOGY = "person_vs_technology"
    PERSON_VS_FATE = "person_vs_fate"
    PERSON_VS_SUPERNATURAL = "person_vs_supernatural"

class StoryTone(Enum):
    LIGHT_HUMOROUS = "Light and Humorous"
    DARK_SERIOUS = "Dark and Serious"
    ROMANTIC_EMOTIONAL = "Romantic and Emotional"
    MYSTERIOUS_SUSPENSEFUL = "Mysterious and Suspenseful"
    EPIC_ADVENTUROUS = "Epic and Adventurous"
    EDUCATIONAL_INFORMATIVE = "Educational and Informative"
    SATIRICAL_CYNICAL = "Satirical and Cynical"

# --- Core Data Models ---

class CharacterInput(BaseModel):
    """Represents raw character information gathered from the user."""
    name: str = Field(..., description="The character's name.")
    role: CharacterRole = Field(..., description="The character's primary role in the story.")
    description: str = Field(..., description="A brief description of the character's appearance, personality, and background.")
    goals: List[str] = Field(default_factory=list, description="The character's main motivations or objectives.")
    traits: List[str] = Field(default_factory=list, description="Key personality traits (e.g., brave, cynical, witty).")
    # Relationships defined better in character_system/relationship_manager
    initial_relationships: Optional[str] = Field(None, description="Brief notes on initial relationships with other characters.")

class SettingInput(BaseModel):
    """Represents raw setting information gathered from the user."""
    time_period: str = Field(..., description="The era or time when the story takes place (e.g., 'Medieval Fantasy', 'Near-future Sci-Fi', 'Present Day').")
    location: str = Field(..., description="The primary physical location(s) (e.g., 'A bustling cyberpunk city', 'A magical forest', 'A small Indian village').")
    atmosphere: Optional[str] = Field(None, description="The overall mood or feeling of the setting (e.g., 'Oppressive', 'Mystical', 'Nostalgic').")
    cultural_context_notes: Optional[str] = Field(None, description="User notes on specific cultural elements, traditions, or social structures relevant to the setting.")

class PlotInput(BaseModel):
    """Represents raw plot information gathered from the user."""
    logline: Optional[str] = Field(None, description="A one-sentence summary of the story.")
    concept_note: Optional[str] = Field(None, description="A more detailed free-text description of the story idea, plot, or concept.")
    primary_conflict: ConflictType = Field(..., description="The main type of conflict driving the story.")
    major_plot_points: List[str] = Field(default_factory=list, description="Key events or turning points mentioned by the user.")
    # These are high-level ideas, detailed structure comes later
    potential_themes: List[str] = Field(default_factory=list, description="Main underlying ideas or messages.")
    desired_tone: StoryTone = Field(..., description="The intended overall tone or mood.")

class CulturalAnalysis(BaseModel):
    """Stores results from cultural context detection."""
    detected_keywords: List[str] = Field(default_factory=list, description="Keywords related to specific cultures or traditions found in input.")
    suggested_frameworks: List[str] = Field(default_factory=list, description="Storytelling frameworks suggested based on context (e.g., 'Panchatantra', 'Ashtarasa').")
    requires_cultural_sensitivity_check: bool = Field(False, description="Flag indicating if careful handling of cultural elements is needed.")

class GenreAnalysis(BaseModel):
    """Stores results from genre classification."""
    primary_genre: Tuple[str, float] = Field(..., description="Predicted primary genre and confidence score.")
    secondary_genres: List[Tuple[str, float]] = Field(default_factory=list, description="Predicted secondary genres above a threshold.")
    genre_specific_prompts: Dict[str, str] = Field(default_factory=dict, description="Suggested follow-up questions or prompts based on primary genre.")

class NLPExtraction(BaseModel):
    """Stores results from NLP analysis of free-text input."""
    extracted_entities: Dict[str, List[str]] = Field(default_factory=dict, description="Entities extracted (e.g., {'PERSON': ['Ajay', 'Priya'], 'LOC': ['Mumbai']}).")
    extracted_themes: List[Tuple[str, float]] = Field(default_factory=list, description="Potential themes identified from text and confidence scores.")
    sentiment: Optional[Tuple[str, float]] = Field(None, description="Overall sentiment of the input text (e.g., ('positive', 0.8)).")


# --- The Final Output of the Input Processing Module ---

class StoryConcept(BaseModel):
    """
    The structured output of the input_processing module.
    This serves as the foundational blueprint for the story_blueprint module.
    """
    # Core User Input (Structured)
    title_suggestion: Optional[str] = Field(None, description="A working title, if provided or generated.")
    target_audience: TargetAudience = Field(..., description="The intended audience.")
    story_length: StoryLength = Field(..., description="The desired overall length.")
    initial_characters: List[CharacterInput] = Field(default_factory=list, description="List of initial character descriptions.")
    initial_setting: SettingInput = Field(..., description="Description of the story's setting.")
    initial_plot: PlotInput = Field(..., description="Core plot ideas and conflicts.")

    # Analysis Results
    genre_analysis: GenreAnalysis = Field(..., description="Results of genre classification.")
    cultural_analysis: CulturalAnalysis = Field(..., description="Results of cultural context detection.")
    nlp_analysis: Optional[NLPExtraction] = Field(None, description="Results from NLP on free-text input, if provided.")

    # Additional Metadata for Downstream Processing
    processing_flags: Dict[str, Any] = Field(default_factory=dict, description="Flags for downstream modules (e.g., {'use_panchatantra_structure': True}).")
    generation_metadata: Dict[str, str] = Field(default_factory=dict, description="Metadata about the generation request (e.g., timestamp, input mode).")

    @field_validator('initial_characters')
    def check_at_least_one_character(cls, v):
        if not v:
            raise ValueError('At least one character must be defined.')
        # TODO: More Complex Validations 
        return v

    class Config:
        use_enum_values = True 