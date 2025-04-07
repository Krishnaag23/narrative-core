#!/usr/bin/env python

import asyncio
import sys
import os
import logging
import json
from typing import Optional, Dict, Any, List


# --- Imports after path setup ---
try:
    # Utilities (Initialize first)
    from src.utils.config import settings
    from src.utils import (
        LLMwrapper,
        VectorStoreInterface,
        PromptManager,
        GraphDB
    )

    # Core Components / Facades
    from src.input_processing import process_user_input_cli, StoryConcept, StoryLength
    from src.character_system import CharacterSystemFacade, CharacterProfile
    from src.memory_management import (
        HierarchicalSummarizer,
        KnowledgeGraphManager,
        ContextOptimizer
        # Import other memory managers if used directly
    )
    from src.story_blueprint import (
        PlotArcGenerator,
        EpisodeMapper,
        NarrativeGraphBuilder
    )
    from src.episode_generator import SceneConstructor, ScriptBuilder
    from src.quality_control import QualityControlFacade, QualityReport
    from src.output_formatter import MetadataGenerator, AudioAdapter, AudioFormat

except ImportError as e:
    print(f"FATAL ERROR: Failed to import necessary modules.")
    print(f"Make sure '{SRC_PATH}' is correct and contains all submodules.")
    print(f"Ensure all dependencies in requirements.txt are installed.")
    print(f"Import error details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"FATAL ERROR during initial imports: {e}")
    sys.exit(1)

# --- Logging Setup ---
# Basic config handled by utils.config, get specific logger
logger = logging.getLogger("NarrativeCorePipeline")
# Ensure logger level matches config if needed, config usually sets root level
# logger.setLevel(settings.LOG_LEVEL.upper())

# --- Helper Function ---
def get_target_episode_count(length_enum: StoryLength) -> int:
    """Maps StoryLength enum to a target number of episodes."""
    if length_enum == StoryLength.SHORT:
        return 3
    elif length_enum == StoryLength.MEDIUM:
        return 7 # Example value
    elif length_enum == StoryLength.LONG:
        return 12 # Example value
    else:
        return 5 # Default fallback

async def save_output(filename: str, content: Any, is_json: bool = False):
    """Helper to save generated output to files for review."""
    output_dir = os.path.join(PROJECT_ROOT, "pipeline_output")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            if is_json:
                json.dump(content, f, indent=2, default=str) # Use default=str for non-serializable types like datetime
            else:
                f.write(str(content))
        logger.info(f"Output saved to: {filepath}")
    except Exception as e:
        logger.error(f"Failed to save output to {filepath}: {e}")


# --- Main Pipeline Function ---
async def run_full_pipeline():
    """Executes the complete Narrative-Core generation pipeline."""
    print("\n" + "="*40)
    print("🚀 STARTING NARRATIVE-CORE PIPELINE 🚀")
    print("="*40 + "\n")

    # --- 0. Initialization ---
    print("--- Initializing Core Components ---")
    try:
        llm_wrapper = LLMwrapper()
        vector_store = VectorStoreInterface()
        prompt_manager = PromptManager() # Reloads prompts on init
        graph_db_instance = GraphDB()

        # Clear graph/vector stores for a clean run (optional)
        # graph_db_instance.clear_graph()
        # logger.info("Cleared Knowledge Graph for new run.")
        # You might need specific logic to clear vector store collections if needed

        # Facades and Managers that depend on utilities
        character_facade = CharacterSystemFacade(llm_wrapper=llm_wrapper)
        summarizer = HierarchicalSummarizer(llm_wrapper=llm_wrapper)
        kg_manager = KnowledgeGraphManager(graph_db_instance=graph_db_instance)
        # Context optimizer needs several components
        context_optimizer = ContextOptimizer(
            llm_wrapper=llm_wrapper,
            summarizer=summarizer,
            kg_manager=kg_manager,
            character_memory=character_facade.memory_manager # Get character memory via facade
        )
        plot_arc_generator = PlotArcGenerator(llm_wrapper=llm_wrapper)
        episode_mapper = EpisodeMapper(llm_wrapper=llm_wrapper) # Pass LLM if refinement needed
        narrative_graph_builder = NarrativeGraphBuilder(graph_db_instance=graph_db_instance)
        scene_constructor = SceneConstructor(llm_wrapper=llm_wrapper)
        script_builder = ScriptBuilder(llm_wrapper=llm_wrapper, character_facade=character_facade)
        qc_facade = QualityControlFacade(llm_wrapper=llm_wrapper)
        metadata_generator = MetadataGenerator(llm_wrapper=llm_wrapper)
        audio_adapter = AudioAdapter()

        print("Core components initialized successfully.\n")
    except Exception as e:
        logger.critical(f"Failed during component initialization: {e}", exc_info=True)
        print(f"\nFATAL ERROR: Could not initialize core components: {e}")
        return

    # --- 1. Input Processing ---
    print("--- Stage 1: Input Processing (CLI) ---")
    story_concept: Optional[StoryConcept] = None
    try:
        story_concept = await process_user_input_cli()
    except Exception as e:
        logger.error(f"Error during input processing: {e}", exc_info=True)
        print(f"\nERROR during input processing: {e}")
        return

    if not story_concept:
        print("\nInput processing cancelled or failed. Exiting pipeline.")
        return

    print("\n--- Input Processing Complete ---")
    print(f"  Title Suggestion: {story_concept.title_suggestion or 'N/A'}")
    print(f"  Primary Genre: {story_concept.genre_analysis.primary_genre[0]} (Score: {story_concept.genre_analysis.primary_genre[1]:.2f})")
    print(f"  Target Audience: {story_concept.target_audience.value}")
    print(f"  Story Length: {story_concept.story_length.value}")
    print(f"  Characters Input: {len(story_concept.initial_characters)}")
    await save_output("1_story_concept.json", story_concept.model_dump(), is_json=True)
    print("  (Full concept saved to pipeline_output/1_story_concept.json)")


    # --- 2. Character Genesis ---
    print("\n--- Stage 2: Character Genesis ---")
    generated_profiles: Dict[str, CharacterProfile] = {} # Store by name for easier access later
    if not story_concept.initial_characters:
        print("No initial characters found in concept.")
    else:
        story_context_for_genesis = story_concept.model_dump(include={
            'genre_analysis', 'initial_setting', 'target_audience'
        })
        print(f"Generating profiles for {len(story_concept.initial_characters)} character(s)...")
        char_tasks = []
        for char_input in story_concept.initial_characters:
             char_tasks.append(
                 character_facade.load_or_create_character(
                    character_input=char_input,
                    story_context=story_context_for_genesis
                )
             )
        # Run character creation concurrently
        try:
            results = await asyncio.gather(*char_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                char_name = story_concept.initial_characters[i].name
                if isinstance(result, CharacterProfile):
                    generated_profiles[result.name] = result # Use name as key
                    print(f"  ✅ Profile generated for: {result.name}")
                    await save_output(f"2_character_{result.name}.json", result.model_dump(), is_json=True)
                elif isinstance(result, Exception):
                    logger.error(f"Error generating profile for {char_name}: {result}", exc_info=result)
                    print(f"  ❌ FAILED generating profile for: {char_name} ({result})")
                else:
                    logger.error(f"Failed generating profile for {char_name} (returned None or unexpected type)")
                    print(f"  ❌ FAILED generating profile for: {char_name}")
        except Exception as e:
            logger.error(f"Unexpected error during character genesis gather: {e}", exc_info=True)
            print(f"  ❌ Unexpected error during character generation batch.")

    if not generated_profiles:
         print("\nNo character profiles generated successfully. Cannot proceed.")
         return
    print("  (Character profiles saved to pipeline_output/2_character_*.json)")


    # --- 3. Story Blueprint ---
    print("\n--- Stage 3: Story Blueprint (Arc, Mapping, Graph) ---")
    plot_arc_data: Optional[Dict[str, Any]] = None
    episode_outlines: List[Dict[str, Any]] = []
    target_ep_count = get_target_episode_count(story_concept.story_length)

    try:
        # Build initial KG
        print("  Building initial knowledge graph...")
        narrative_graph_builder.build_initial_graph(story_concept)

        # Generate Plot Arc
        print("  Generating plot arc using LLM...")
        plot_arc_data = await plot_arc_generator.generate_arc(story_concept)

        if not plot_arc_data or "plot_arc" not in plot_arc_data:
             if plot_arc_data and "raw_llm_output" in plot_arc_data:
                  print("  ❌ Plot arc generation failed to produce valid JSON. Raw output:")
                  print(plot_arc_data["raw_llm_output"][:500] + "...")
                  await save_output("3a_plot_arc_raw_error.txt", plot_arc_data["raw_llm_output"])
             else:
                print("  ❌ Plot arc generation failed (No LLM response or invalid data).")
             return # Cannot proceed without plot arc

        print(f"  ✅ Plot arc generated with {len(plot_arc_data.get('plot_arc',[]))} stages.")
        await save_output("3a_plot_arc.json", plot_arc_data, is_json=True)

        # Add Arc to KG
        print("  Adding plot arc to knowledge graph...")
        narrative_graph_builder.add_plot_arc_to_graph(plot_arc_data, story_concept)

        # Map to Episodes
        print(f"  Mapping arc to {target_ep_count} episode outlines...")
        episode_outlines = episode_mapper.map_plot_to_episodes(plot_arc_data, target_ep_count)

        if not episode_outlines:
            print("  ❌ Episode mapping failed.")
            return
        print(f"  ✅ Mapped into {len(episode_outlines)} episode outlines.")
        await save_output("3b_episode_outlines.json", episode_outlines, is_json=True)


        # Add Episode Structure to KG
        print("  Adding episode structure to knowledge graph...")
        narrative_graph_builder.add_episode_structure_to_graph(episode_outlines)

        # Save graph (if using NetworkX)
        try:
             graph_obj = narrative_graph_builder.get_graph()
             if graph_obj:
                  import networkx as nx
                  nx.write_gml(graph_obj, os.path.join(PROJECT_ROOT, "pipeline_output", "3c_narrative_graph.gml"))
                  print("  (Narrative graph saved to pipeline_output/3c_narrative_graph.gml)")
        except Exception as graph_err:
             logger.warning(f"Could not save narrative graph: {graph_err}")


    except Exception as e:
        logger.error(f"Error during story blueprinting: {e}", exc_info=True)
        print(f"\nERROR during story blueprinting: {e}")
        return


    # --- 4. Episode Generation ---
    print("\n--- Stage 4: Episode Generation ---")
    generated_scripts: List[Dict[str, Any]] = []
    # Store summaries for QC checks later
    episode_summaries_for_qc: Dict[int, str] = {}

    print(f"Generating scripts for {len(episode_outlines)} episodes...")
    # Run sequentially for simplicity, could be parallelized with care
    for outline in episode_outlines:
        ep_num = outline.get("episode_number")
        print(f"  Generating Episode {ep_num}...")
        try:
            final_script = await script_builder.build_episode_script(
                episode_outline=outline,
                character_profiles=generated_profiles # Pass name->profile map
            )
            if final_script:
                generated_scripts.append(final_script)
                print(f"  ✅ Script generated for Episode {ep_num}.")
                await save_output(f"4_episode_{ep_num}_script.json", final_script, is_json=True)

                # Generate summary for QC
                ep_summary = await summarizer.summarize_episode(final_script)
                if ep_summary:
                     episode_summaries_for_qc[ep_num] = ep_summary
                else:
                     # Use outline summary as fallback for QC
                     episode_summaries_for_qc[ep_num] = outline.get("summary_objective", f"Summary missing for Ep {ep_num}")

            else:
                print(f"  ❌ FAILED to generate script for Episode {ep_num}.")
        except Exception as e:
            logger.error(f"Error generating script for Episode {ep_num}: {e}", exc_info=True)
            print(f"  ❌ ERROR generating script for Episode {ep_num}: {e}")

    if len(generated_scripts) != len(episode_outlines):
        print(f"\nWarning: Only {len(generated_scripts)} out of {len(episode_outlines)} episodes were generated successfully.")
    if not generated_scripts:
         print("\nNo episode scripts were generated. Cannot proceed.")
         return
    print("  (Episode scripts saved to pipeline_output/4_episode_*_script.json)")


    # --- 5. Quality Control ---
    print("\n--- Stage 5: Quality Control ---")
    quality_report: Optional[QualityReport] = None
    try:
        print("  Running automated quality checks...")
        # Need character profiles mapped by ID for QC facade if it uses IDs
        profiles_by_id = {p.character_id: p for p in generated_profiles.values()}
        quality_report = await qc_facade.run_all_checks(
            story_concept=story_concept,
            generated_episodes=generated_scripts, # Pass the generated script data
            character_profiles=profiles_by_id
        )
        if quality_report:
             print(f"  ✅ Quality Check Complete - Score: {quality_report.overall_score:.2f}, Passed: {quality_report.passed}")
             print(f"  Number of Issues Found: {len(quality_report.issues)}")
             await save_output("5_quality_report.json", quality_report.model_dump(), is_json=True)
             print("  (Quality report saved to pipeline_output/5_quality_report.json)")
        else:
            print("  ❌ Quality check failed to produce a report.")

    except Exception as e:
        logger.error(f"Error during quality control checks: {e}", exc_info=True)
        print(f"\nERROR during quality control: {e}")
        # Continue to output formatting even if QC fails? Optional.


    # --- 6. Output Formatting ---
    print("\n--- Stage 6: Output Formatting ---")
    print("  Generating metadata and audio-formatted script (Example: Episode 1)...")
    if generated_scripts:
        try:
            first_episode_script = generated_scripts[0]
            ep_num = first_episode_script.get("episode_number", 1)
            elements = first_episode_script.get("scenes", [{}])[0].get("elements", []) # Get elements from first scene for example

            # Generate Metadata
            metadata = await metadata_generator.generate_episode_metadata(
                story_concept=story_concept,
                # Pass elements from all scenes of the episode
                episode_script_elements=[el for scene in first_episode_script.get("scenes", []) for el in scene.get("elements", [])],
                episode_number=ep_num
            )
            print(f"\n  Metadata for Episode {ep_num}:")
            print(json.dumps(metadata, indent=2, default=str))
            await save_output(f"6a_episode_{ep_num}_metadata.json", metadata, is_json=True)

            # Format for Audio (Simple Text)
            audio_text = audio_adapter.format_for_audio(
                # Pass elements from all scenes
                episode_script_elements=[el for scene in first_episode_script.get("scenes", []) for el in scene.get("elements", [])],
                format_type=AudioFormat.SIMPLE_TEXT
            )
            print(f"\n  Audio-Formatted Text (Simple) for Episode {ep_num} (Snippet):\n---")
            print(audio_text[:1000] + "\n---") # Print snippet
            await save_output(f"6b_episode_{ep_num}_audio_simple.txt", audio_text)
            print(f"  (Metadata and audio format for Ep {ep_num} saved to pipeline_output/)")

        except Exception as e:
            logger.error(f"Error during output formatting: {e}", exc_info=True)
            print(f"\nERROR during output formatting: {e}")
    else:
        print("  No scripts available to format.")


    # --- 7. Completion ---
    print("\n" + "="*40)
    print("✅ NARRATIVE-CORE PIPELINE COMPLETE ✅")
    print("="*40 + "\n")


# --- Run the async function ---
if __name__ == "__main__":
    # Make sure necessary setup (like .env file) is done
    if not settings.OPENAI_API_KEY:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ERROR: OPENAI_API_KEY is not set in .env file. !!!")
        print("!!! Please create a .env file in the project root  !!!")
        print("!!! and add: OPENAI_API_KEY='sk-your-key-here'     !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        sys.exit(1)

    print("NOTE: This script will run the full story generation pipeline.")
    print("It starts with an interactive CLI for the story concept.")
    print("It will make multiple API calls to OpenAI.")
    print("Generated files will be saved in the 'pipeline_output' directory.")
    # input("Press Enter to start the pipeline...") # Optional confirmation

    try:
        asyncio.run(run_full_pipeline())
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user.")
    except Exception as main_err:
         logger.critical(f"Unhandled exception in main pipeline execution: {main_err}", exc_info=True)
         print(f"\nFATAL PIPELINE ERROR: {main_err}")