"""
End-to-end test script demonstrating the flow from Input Processing
to Character System initialization.
"""

import asyncio
import sys
import os
import logging
from typing import Optional, Dict, Any

# --- Path Setup ---
# Add the 'src' directory to the Python path
# This assumes the script is run from the project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# --- Imports after path setup ---
try:
    from src.utils.config import settings # To ensure config is loaded first
    from src.input_processing import process_user_input_cli, StoryConcept
    from src.character_system import CharacterSystemFacade, CharacterProfile, CharacterInput
except ImportError as e:
    print(f"ERROR: Failed to import necessary modules.")
    print(f"Make sure '{SRC_PATH}' is correct and contains the modules.")
    print(f"Import error details: {e}")
    sys.exit(1)

# --- Logging Setup ---
# Basic config is handled by utils.config, but we can get a specific logger
logger = logging.getLogger("TestFlowScript")
logger.setLevel(settings.LOG_LEVEL.upper()) # Ensure logger level matches config

# --- Main Test Function ---
async def run_test():
    """Executes the input processing and character system test flow."""
    logger.info("Starting End-to-End Test Flow...")
    print("\n" + "="*30)
    print(" STAGE 1: INPUT PROCESSING ")
    print("="*30 + "\n")

    story_concept: Optional[StoryConcept] = None
    try:
        # This function runs the interactive CLI
        story_concept = await process_user_input_cli()
    except Exception as e:
        logger.error(f"An error occurred during input processing: {e}", exc_info=True)
        print(f"\nERROR during input processing: {e}")
        return # Stop the test

    if not story_concept:
        logger.warning("Input processing was cancelled or failed. Exiting test.")
        print("\nInput processing did not complete. Test aborted.")
        return

    logger.info("Input processing completed successfully.")
    print("\n" + "="*30)
    print(" INPUT PROCESSING RESULTS ")
    print("="*30)
    try:
        print(f"  Target Audience: {story_concept.target_audience}")
        print(f"  Story Length: {story_concept.story_length}")
        print(f"  Primary Genre: {story_concept.genre_analysis.primary_genre[0]} (Score: {story_concept.genre_analysis.primary_genre[1]:.2f})")
        print(f"  Cultural Keywords: {story_concept.cultural_analysis.detected_keywords or 'None'}")
        print(f"  Number of Initial Characters: {len(story_concept.initial_characters)}")
        # Optionally print more details from story_concept
        # print(story_concept.model_dump_json(indent=2))
    except AttributeError as e:
         logger.error(f"Error accessing attributes of story_concept: {e}. Structure might be unexpected.", exc_info=True)
         print(f"\nWarning: Could not display all story concept details due to error: {e}")
    except Exception as e:
         logger.error(f"Unexpected error displaying story_concept details: {e}", exc_info=True)
         print(f"\nWarning: Could not display story concept details due to error: {e}")


    print("\n" + "="*30)
    print(" STAGE 2: CHARACTER SYSTEM - GENESIS ")
    print("="*30 + "\n")

    # Initialize the Character System Facade
    # It now handles its own dependencies via utils
    try:
        character_facade = CharacterSystemFacade()
    except Exception as e:
        logger.critical(f"Failed to initialize CharacterSystemFacade: {e}", exc_info=True)
        print(f"\nFATAL ERROR: Could not initialize the Character System: {e}")
        return

    generated_profiles: Dict[str, CharacterProfile] = {}

    if not story_concept.initial_characters:
        logger.warning("Story concept has no initial characters defined.")
        print("No characters found in the story concept to process.")
    else:
        print(f"Attempting to generate profiles for {len(story_concept.initial_characters)} characters...")
        # Create context dictionary for genesis (can be expanded)
        story_context_for_genesis = story_concept.model_dump(include={
            'genre_analysis', 'initial_setting', 'target_audience'
            })

        # Process each character input
        for char_input in story_concept.initial_characters:
            print(f"\nProcessing character: {char_input.name} ({char_input.role})")
            logger.info(f"Calling character genesis for {char_input.name}...")
            try:
                # Call the async genesis function
                profile: Optional[CharacterProfile] = await character_facade.load_or_create_character(
                    character_input=char_input,
                    story_context=story_context_for_genesis
                )

                if profile:
                    generated_profiles[profile.character_id] = profile
                    logger.info(f"Successfully generated profile for {profile.name} ({profile.character_id})")
                    print(f"  -> Profile generated successfully for {profile.name}!")
                else:
                    logger.error(f"Failed to generate profile for {char_input.name}.")
                    print(f"  -> FAILED to generate profile for {char_input.name}.")

            except Exception as e:
                logger.error(f"An error occurred during character genesis for {char_input.name}: {e}", exc_info=True)
                print(f"  -> ERROR during profile generation for {char_input.name}: {e}")

    # --- Display Character Results ---
    print("\n" + "="*30)
    print(" CHARACTER GENERATION RESULTS ")
    print("="*30)

    if not generated_profiles:
        print("\nNo character profiles were successfully generated.")
    else:
        print(f"\nSuccessfully generated {len(generated_profiles)} character profiles:")
        for char_id, profile in generated_profiles.items():
            print(f"\n--- Character: {profile.name} ({profile.role}) ---")
            print(f"  ID: {char_id}")
            print(f"  Core Traits: {', '.join(profile.core_traits)}")
            print(f"  Motivations: {', '.join(profile.motivations)}")
            print(f"  Goals: {', '.join(profile.goals)}")
            print(f"  Flaws: {', '.join(profile.flaws)}")
            print(f"  Backstory (Snippet): {profile.backstory[:150]}...") # Show snippet
            print(f"  Voice: {profile.voice_description}")
            # Check vector store embeddings (optional advanced check)
            # aspects = character_facade.embedding_manager.get_aspects_for_character(char_id)
            # print(f"  Vector Store Aspects Count: {len(aspects)}")


    logger.info("End-to-End Test Flow Completed.")
    print("\n" + "="*30)
    print(" TEST FLOW COMPLETED ")
    print("="*30 + "\n")

# --- Run the async function ---
if __name__ == "__main__":
    # Make sure necessary setup (like .env file) is done
    if not settings.OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY is not set in your environment or .env file.")
        print("Please set it up before running the test.")
        sys.exit(1)

    print("NOTE: This script will interactively ask for story input.")
    print("It will then make API calls to OpenAI for character generation.")
    input("Press Enter to start the test...")

    asyncio.run(run_test())