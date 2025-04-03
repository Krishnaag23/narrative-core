"""
Defines Pydantic models for structuring quality control results.
"""

from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Severity(Enum):
    """Severity level of a detected issue."""
    INFO = "Info"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class Issue(BaseModel):
    """Represents a single issue found during quality checks."""
    severity: Severity = Field(..., description="How severe the issue is.")
    checker: str = Field(..., description="The name of the checker that found the issue (e.g., 'CoherenceChecker', 'CulturalValidator').")
    check_type: str = Field(..., description="Specific check that failed (e.g., 'PlotLogic', 'CharacterConsistency', 'Sensitivity').")
    description: str = Field(..., description="Detailed explanation of the issue.")
    location: Optional[str] = Field(None, description="Where the issue occurred (e.g., 'Episode 3, Scene 5', 'Character: Arjun').")
    suggestion: Optional[str] = Field(None, description="Optional suggestion for fixing the issue.")

class QualityReport(BaseModel):
    """Aggregated report summarizing the results of all quality checks."""
    timestamp: datetime = Field(default_factory=datetime.now)
    overall_score: float = Field(..., ge=0.0, le=1.0, description="A calculated score reflecting overall quality (1.0 = best).")
    issues: List[Issue] = Field(default_factory=list, description="A list of all detected issues.")
    passed: bool = Field(..., description="Whether the content passed minimum quality thresholds.")

    # Example method to calculate score (can be customized)
    def calculate_score(self):
        """Calculates a score based on the severity and number of issues."""
        if not self.issues:
            self.overall_score = 1.0
            self.passed = True
            return

        penalty = 0.0
        high_critical_count = 0
        for issue in self.issues:
            if issue.severity == Severity.CRITICAL:
                penalty += 0.5
                high_critical_count += 1
            elif issue.severity == Severity.HIGH:
                penalty += 0.2
                high_critical_count += 1
            elif issue.severity == Severity.MEDIUM:
                penalty += 0.05
            elif issue.severity == Severity.LOW:
                penalty += 0.01
            # INFO severity doesn't penalize score

        # Simple scoring logic: start at 1.0 and subtract penalties
        self.overall_score = max(0.0, 1.0 - penalty)
        # Pass if score is above a threshold (e.g., 0.7) and no critical/high issues
        self.passed = self.overall_score >= 0.7 and high_critical_count == 0