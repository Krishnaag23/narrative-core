from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

class PointOfView(Enum):
    FIRST_PERSON = "first_person"
    THIRD_PERSON_LIMITED = "third_person_limited"
    THIRD_PERSON_OMNISCIENT = "third_person_omniscient"

class ConflictType(Enum):
    PERSON_VS_PERSON = "person_vs_person"
    PERSON_VS_NATURE = "person_vs_nature"
    PERSON_VS_SOCIETY = "person_vs_society"
    PERSON_VS_SELF = "person_vs_self"
    PERSON_VS_TECHNOLOGY = "person_vs_technology"
    PERSON_VS_FATE = "person_vs_fate"

@dataclass
class Character:
    name: str
    role: str  # protagonist, antagonist, supporting
    description: str
    goals: List[str]
    traits: List[str]
    relationships: Dict[str, str]  # name: relationship_type

@dataclass
class Setting:
    time_period: str
    location: str
    cultural_context: str
    environment_description: str

@dataclass
class Plot:
    exposition: str
    rising_action: List[str]
    climax: str
    falling_action: List[str]
    resolution: str

@dataclass
class StoryElements:
    characters: List[Character]
    plot: Plot
    setting: Setting
    themes: List[str]
    point_of_view: PointOfView
    conflict: ConflictType
    tone: str
