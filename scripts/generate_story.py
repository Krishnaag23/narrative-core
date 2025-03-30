#!/usr/bin/env python

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from input_processing import process_user_input_cli, StoryConcept

def main():
    print("=" * 30)
    print(" NarrativeCore Story Generation ")
    print("=" * 30)

    # --- Stage 1: Input Processing ---
    story_concept: StoryConcept | None = process_user_input_cli()

    if not story_concept:
        print("\nStory concept generation failed or was cancelled. Exiting.")
        return

    print("\n--- Input Processing Complete ---")
    print(f"Primary Genre: {story_concept.genre_analysis.primary_genre[0]}")
    print(f"Target Audience: {story_concept.target_audience}")
    print(f"Detected Cultural Keywords: {story_concept.cultural_analysis.detected_keywords}")
    # print("\nFull Story Concept:") # Optional: print full details
    # print(story_concept.json(indent=2))

    # --- Stage 2: Story Blueprint (Example Placeholder) ---
    print("\n--- Proceeding to Story Blueprint Generation (Placeholder) ---")
    # blueprint = create_blueprint(story_concept)
    # if blueprint:
    #    print("Story Blueprint generated.")
    #    # ... proceed to next stages
    # else:
    #    print("Failed to generate Story Blueprint.")

    # --- Add other stages as they are developed ---

    print("\n--- Pipeline Complete (Partial) ---")


if __name__ == "__main__":
    main()