#!/usr/bin/env python

import asyncio
import sys
import os
import logging
import json
import argparse # For command-line arguments
from typing import Optional, Dict, Any, List

NODE_CHARACTER = "Character"
NODE_LOCATION = "Location"
NODE_EVENT = "Event"
NODE_EPISODE = "Episode"
NODE_THEME = "Theme"
NODE_OBJECT = "Object" # Added node type

REL_INTERACTS_WITH = "INTERACTS_WITH"
REL_LOCATED_IN = "LOCATED_IN"
REL_PART_OF = "PART_OF" # e.g., Event PART_OF Episode
REL_HAS_TRAIT = "HAS_TRAIT"
REL_HAS_GOAL = "HAS_GOAL"
REL_AFFECTS = "AFFECTS" # e.g., Event AFFECTS Character
REL_MENTIONS = "MENTIONS" # e.g., Dialogue MENTIONS Object/Character
REL_LEADS_TO = "LEADS_TO" # e.g., Event LEADS_TO Event
REL_CONTAINS = "CONTAINS"

# --- Path Setup ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

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
    )
    from src.story_blueprint import (
        PlotArcGenerator,
        EpisodeMapper,
        NarrativeGraphBuilder
    )
    from src.episode_generator import SceneConstructor, ScriptBuilder
    from src.quality_control import QualityControlFacade, QualityReport, Issue, Severity
    from src.output_formatter import MetadataGenerator, AudioAdapter, AudioFormat

except ImportError as e:
    print(f"FATAL ERROR: Failed to import necessary modules.")
    print(f"Make sure '{SRC_PATH}' is correct and contains all submodules.")
    print(f"Ensure all dependencies in requirements.txt are installed (including networkx, matplotlib).")
    print(f"Import error details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"FATAL ERROR during initial imports: {e}")
    sys.exit(1)

# --- Logging Setup ---
logger = logging.getLogger("NarrativeCorePipeline")

# --- Helper Functions ---
def get_target_episode_count(length_enum_str: str, override: Optional[int] = None) -> int:
    """Maps StoryLength string or uses override to get episode count."""
    if override is not None and override > 0:
        return override
    length_map = {
        StoryLength.SHORT.value: 2, # Shortened for faster demo
        StoryLength.MEDIUM.value: 4, # Shortened for faster demo
        StoryLength.LONG.value: 6,  # Shortened for faster demo
    }
    default_count = 3 # Default if mapping fails
    count = length_map.get(length_enum_str, default_count)
    logger.info(f"Determined target episode count: {count} (based on '{length_enum_str}' and override '{override}')")
    return count


async def save_output(filename: str, content: Any, is_json: bool = False):
    """Helper to save generated output to files for review."""
    output_dir = os.path.join(PROJECT_ROOT, "pipeline_output")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            if is_json:
                # Use default=str for potential non-serializable types like enums, datetime
                json.dump(content, f, indent=2, default=str)
            else:
                f.write(str(content))
        logger.info(f"Output saved to: {filepath}")
    except Exception as e:
        logger.error(f"Failed to save output to {filepath}: {e}")

def print_header(title: str):
    """Prints a formatted header."""
    print("\n" + "="*10 + f" {title} " + "="*(50 - len(title)))

def print_subheader(title: str):
     """Prints a formatted subheader."""
     print("\n" + "-"*5 + f" {title} " + "-"*(45 - len(title)))


# --- Main Pipeline Function ---
async def run_full_pipeline(args):
    """Executes the complete Narrative-Core generation pipeline."""
    print_header("🚀 STARTING NARRATIVE-CORE PIPELINE 🚀")

    # --- 0. Initialization ---
    print_subheader("Initializing Core Components")
    try:
        llm_wrapper = LLMwrapper()
        vector_store = VectorStoreInterface() # RAG DB should be populated before running this
        prompt_manager = PromptManager()
        graph_db_instance = GraphDB()

        # Facades and Managers
        character_facade = CharacterSystemFacade(llm_wrapper=llm_wrapper)
        summarizer = HierarchicalSummarizer(llm_wrapper=llm_wrapper)
        kg_manager = KnowledgeGraphManager(graph_db_instance=graph_db_instance)
        context_optimizer = ContextOptimizer(
            llm_wrapper=llm_wrapper, summarizer=summarizer, kg_manager=kg_manager,
            character_memory=character_facade.memory_manager
        )
        plot_arc_generator = PlotArcGenerator(llm_wrapper=llm_wrapper)
        episode_mapper = EpisodeMapper(llm_wrapper=llm_wrapper) # LLM needed for refinement
        narrative_graph_builder = NarrativeGraphBuilder(graph_db_instance=graph_db_instance)
        # Scene constructor now within ScriptBuilder
        script_builder = ScriptBuilder(llm_wrapper=llm_wrapper, character_facade=character_facade)
        qc_facade = QualityControlFacade(llm_wrapper=llm_wrapper)
        metadata_generator = MetadataGenerator(llm_wrapper=llm_wrapper)
        audio_adapter = AudioAdapter()

        print("Core components initialized successfully.")
        print(f"LLM Model: {settings.LLM_MODEL_NAME}")
        print(f"Vector DB Path: {settings.VECTOR_DB_PATH}")
        print(f"Verbose Context: {settings.DEMO_VERBOSE_CONTEXT}")
        print("NOTE: Ensure 'scripts/populate_rag_db.py' has been run at least once.")

    except Exception as e:
        logger.critical(f"Failed during component initialization: {e}", exc_info=True)
        print(f"\nFATAL ERROR: Could not initialize core components: {e}")
        return

    # --- 1. Input Processing ---
    print_header("Stage 1: Input Processing (CLI)")
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
    print(f"  Cultural Keywords (Keywords+RAG): {story_concept.cultural_analysis.detected_keywords or 'None'}")
    print(f"  Cultural Frameworks Suggested: {story_concept.cultural_analysis.suggested_frameworks or 'None'}")
    await save_output("1_story_concept.json", story_concept.model_dump(), is_json=True)
    print("  (Full concept saved to pipeline_output/1_story_concept.json)")


    # --- 2. Character Genesis ---
    print_header("Stage 2: Character Genesis")
    generated_profiles_dict: Dict[str, CharacterProfile] = {} # Store by name
    if not story_concept.initial_characters:
        print("No initial characters found in concept.")
    else:
        # ... (rest of character genesis logic is mostly fine, ensure prints are clear) ...
        story_context_for_genesis = story_concept.model_dump(include={
            'genre_analysis', 'initial_setting', 'target_audience'
        })
        print(f"Generating profiles for {len(story_concept.initial_characters)} character(s)...")
        char_tasks = [
            character_facade.load_or_create_character(
                char_input, story_context=story_context_for_genesis
            ) for char_input in story_concept.initial_characters
        ]
        try:
            results = await asyncio.gather(*char_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                char_name = story_concept.initial_characters[i].name
                if isinstance(result, CharacterProfile):
                    generated_profiles_dict[result.name] = result
                    print(f"  ✅ Profile generated for: {result.name}")
                    print(f"     > Traits: {', '.join(result.core_traits)}")
                    print(f"     > Backstory Snippet: {result.backstory[:150]}...")
                    await save_output(f"2_character_{result.name}.json", result.model_dump(), is_json=True)
                # ... (error handling remains the same) ...
                elif isinstance(result, Exception):
                     logger.error(f"Error generating profile for {char_name}: {result}", exc_info=result)
                     print(f"  ❌ FAILED generating profile for: {char_name} ({result})")
                else:
                     logger.error(f"Failed generating profile for {char_name} (returned None or unexpected type)")
                     print(f"  ❌ FAILED generating profile for: {char_name}")
        except Exception as e:
            logger.error(f"Unexpected error during character genesis gather: {e}", exc_info=True)
            print(f"  ❌ Unexpected error during character generation batch.")


    if not generated_profiles_dict:
         print("\nNo character profiles generated successfully. Cannot proceed.")
         return
    print("  (Character profiles saved to pipeline_output/2_character_*.json)")


    # --- 3. Story Blueprint ---
    print_header("Stage 3: Story Blueprint (Arc, Mapping, Graph)")
    plot_arc_data: Optional[Dict[str, Any]] = None
    episode_outlines: List[Dict[str, Any]] = []
    target_ep_count = get_target_episode_count(story_concept.story_length.value, args.episodes)

    try:
        print_subheader("Building Initial Knowledge Graph")
        narrative_graph_builder.build_initial_graph(story_concept)
        print("  Initial graph nodes (Characters, Location, Themes) added.")

        print_subheader("Generating Plot Arc")
        plot_arc_data = await plot_arc_generator.generate_arc(story_concept)
        # ... (rest of plot arc generation and saving logic is mostly fine) ...
        if not plot_arc_data or "plot_arc" not in plot_arc_data:
            # ... (error handling) ...
            return

        print(f"  ✅ Plot arc generated with {len(plot_arc_data.get('plot_arc',[]))} stages.")
        for i, stage in enumerate(plot_arc_data.get('plot_arc', [])):
            print(f"     Stage {i+1}: {stage.get('stage_name')} - Points: {len(stage.get('plot_points', []))}")
        await save_output("3a_plot_arc.json", plot_arc_data, is_json=True)


        print_subheader("Adding Plot Arc to Knowledge Graph")
        narrative_graph_builder.add_plot_arc_to_graph(plot_arc_data, story_concept)
        print("  Plot points and relationships added to graph.")

        print_subheader("Mapping Arc to Episodes")
        episode_outlines = episode_mapper.map_plot_to_episodes(plot_arc_data, target_ep_count)
        # ... (rest of mapping and saving logic is fine) ...
        if not episode_outlines:
             print("  ❌ Episode mapping failed.")
             return
        print(f"  ✅ Mapped into {len(episode_outlines)} episode outlines.")
        await save_output("3b_episode_outlines.json", episode_outlines, is_json=True)

        print_subheader("Adding Episode Structure to Knowledge Graph")
        narrative_graph_builder.add_episode_structure_to_graph(episode_outlines)
        print("  Episode nodes linked to plot points in graph.")

        # Attempt Visualization
        print_subheader("Visualizing Knowledge Graph (Attempt)")
        try:
             graph_obj = narrative_graph_builder.get_graph()
             if graph_obj and graph_obj.number_of_nodes() > 0:
                  import matplotlib.pyplot as plt
                  import networkx as nx
                  plt.figure(figsize=(15, 10))
                  pos = nx.spring_layout(graph_obj, k=0.3, iterations=50) # Adjust layout params

                  # Color nodes by type
                  node_colors = []
                  node_labels = {}
                  for node, data in graph_obj.nodes(data=True):
                       node_type = data.get('type', 'Unknown')
                       node_labels[node] = f"{node}\n({node_type})" # Label with ID and type
                       if node_type == NODE_CHARACTER: node_colors.append('skyblue')
                       elif node_type == NODE_LOCATION: node_colors.append('lightgreen')
                       elif node_type == NODE_EPISODE: node_colors.append('salmon')
                       elif node_type == NODE_PLOT_POINT: node_colors.append('lightcoral')
                       elif node_type == NODE_THEME: node_colors.append('gold')
                       else: node_colors.append('grey')

                  nx.draw(graph_obj, pos,
                          labels=node_labels,
                          node_color=node_colors,
                          with_labels=True,
                          node_size=2000, # Adjust size
                          font_size=8,    # Adjust font size
                          alpha=0.8,
                          edge_color='gray')

                  # Add edge labels (relationship type) - can get cluttered
                  # edge_labels = {(u, v): d.get('type', '') for u, v, d in graph_obj.edges(data=True)}
                  # nx.draw_networkx_edge_labels(graph_obj, pos, edge_labels=edge_labels, font_size=6)

                  graph_img_path = os.path.join(PROJECT_ROOT, "pipeline_output", "3c_narrative_graph.png")
                  plt.title("Narrative Knowledge Graph")
                  plt.savefig(graph_img_path)
                  plt.close() # Close plot to free memory
                  print(f"  ✅ Graph visualization saved to: {graph_img_path}")
             else:
                  print("  Graph is empty, skipping visualization.")
             # Also save GML for detailed inspection
             if graph_obj:
                  nx.write_gml(graph_obj, os.path.join(PROJECT_ROOT, "pipeline_output", "3c_narrative_graph.gml"))
                  print("  (Graph data also saved to pipeline_output/3c_narrative_graph.gml)")

        except ImportError:
             logger.warning("Matplotlib or NetworkX not found. Cannot visualize graph. Skipping visualization.")
             print("  Skipping graph visualization (matplotlib/networkx not installed).")
        except Exception as graph_err:
             logger.warning(f"Could not visualize or save narrative graph: {graph_err}")
             print(f"  Graph visualization/saving failed: {graph_err}")

    except Exception as e:
        logger.error(f"Error during story blueprinting: {e}", exc_info=True)
        print(f"\nERROR during story blueprinting: {e}")
        return

    # --- 4. Episode Generation ---
    print_header("Stage 4: Episode Generation")
    generated_scripts: List[Dict[str, Any]] = []
    episode_summaries_for_qc: Dict[int, str] = {}

    print(f"Generating scripts for {len(episode_outlines)} episodes...")
    for outline in episode_outlines:
        ep_num = outline.get("episode_number")
        print_subheader(f"Generating Episode {ep_num}")
        try:
            # Note: ScriptBuilder internally calls SceneConstructor and DialogueGenerator
            final_script = await script_builder.build_episode_script(
                episode_outline=outline,
                character_profiles=generated_profiles_dict # Pass name->profile map
            )
            if final_script:
                generated_scripts.append(final_script)
                print(f"  ✅ Script generated for Episode {ep_num}.")
                # Print snippet of the script
                print("     Script Snippet (First Scene Start):")
                if final_script.get("scenes"):
                     first_scene_elements = final_script["scenes"][0].get("elements", [])[:3] # First 3 elements
                     for el in first_scene_elements:
                          print(f"       - {el.get('type', '')}: {str(el.get('content', ''))[:80]}...")
                await save_output(f"4_episode_{ep_num}_script.json", final_script, is_json=True)

                # Generate summary for QC & next step context (if needed)
                print("     Generating episode summary...")
                ep_summary = await summarizer.summarize_episode(final_script)
                if ep_summary:
                     episode_summaries_for_qc[ep_num] = ep_summary
                     print(f"     Summary: {ep_summary[:150]}...")
                else:
                     episode_summaries_for_qc[ep_num] = outline.get("summary_objective", f"Summary missing for Ep {ep_num}")
                     print("     Failed to generate summary.")

            else:
                print(f"  ❌ FAILED to generate script for Episode {ep_num}.")
        except Exception as e:
            logger.error(f"Error generating script for Episode {ep_num}: {e}", exc_info=True)
            print(f"  ❌ ERROR generating script for Episode {ep_num}: {e}")

    # ... (rest of episode generation logic is mostly fine) ...
    if not generated_scripts:
         print("\nNo episode scripts were generated. Cannot proceed.")
         return
    print("  (Full episode scripts saved to pipeline_output/4_episode_*_script.json)")

    # --- 5. Quality Control ---
    print_header("Stage 5: Quality Control")
    quality_report: Optional[QualityReport] = None
    try:
        print("  Running automated quality checks...")
        profiles_by_id = {p.character_id: p for p in generated_profiles_dict.values()}
        quality_report = await qc_facade.run_all_checks(
            story_concept=story_concept,
            # Need summaries within the generated_scripts dicts or pass episode_summaries_for_qc
            generated_episodes=[{**script, "summary": episode_summaries_for_qc.get(script.get("episode_number"))} for script in generated_scripts],
            character_profiles=profiles_by_id
        )
        if quality_report:
             print(f"  ✅ Quality Check Complete - Score: {quality_report.overall_score:.2f}, Passed: {quality_report.passed}")
             print(f"  Number of Issues Found: {len(quality_report.issues)}")
             if quality_report.issues:
                  print("  Issues:")
                  for issue in quality_report.issues[:5]: # Print top 5 issues
                       print(f"    - [{issue.severity.value} / {issue.checker} / {issue.check_type}] {issue.description} (Loc: {issue.location or 'N/A'})")
                  if len(quality_report.issues) > 5: print("      ...")
             await save_output("5_quality_report.json", quality_report.model_dump(), is_json=True)
             print("  (Full quality report saved to pipeline_output/5_quality_report.json)")
        else:
            print("  ❌ Quality check failed to produce a report.")

    # ... (rest of QC logic is fine) ...
    except Exception as e:
         logger.error(f"Error during quality control checks: {e}", exc_info=True)
         print(f"\nERROR during quality control: {e}")


    # --- 6. Output Formatting ---
    print_header("Stage 6: Output Formatting")
    print("  Generating metadata and audio format for Episode 1...")
    if generated_scripts:
        # ... (Metadata generation logic is fine) ...
        # ... (Audio formatting logic is fine) ...
        try:
             first_episode_script = generated_scripts[0]
             ep_num = first_episode_script.get("episode_number", 1)
             all_elements_ep1 = [el for scene in first_episode_script.get("scenes", []) for el in scene.get("elements", [])]

             print_subheader(f"Generating Metadata for Episode {ep_num}")
             metadata = await metadata_generator.generate_episode_metadata(
                 story_concept=story_concept,
                 episode_script_elements=all_elements_ep1,
                 episode_number=ep_num
             )
             print(f"  Metadata:")
             print(json.dumps(metadata, indent=4, default=str))
             await save_output(f"6a_episode_{ep_num}_metadata.json", metadata, is_json=True)

             print_subheader(f"Generating Simple Audio Text for Episode {ep_num}")
             audio_text = audio_adapter.format_for_audio(
                 episode_script_elements=all_elements_ep1,
                 format_type=AudioFormat.SIMPLE_TEXT
             )
             print(f"  Audio Text (Snippet):\n---\n{audio_text[:1000]}\n---")
             await save_output(f"6b_episode_{ep_num}_audio_simple.txt", audio_text)

             print_subheader(f"Generating SSML Audio Format for Episode {ep_num}")
             ssml_text = audio_adapter.format_for_audio(
                 episode_script_elements=all_elements_ep1,
                 format_type=AudioFormat.SSML
             )
             print(f"  SSML (Snippet):\n---\n{ssml_text[:1000]}\n---")
             await save_output(f"6c_episode_{ep_num}_audio_ssml.xml", ssml_text)

             print(f"  (Metadata and audio formats for Ep {ep_num} saved to pipeline_output/)")

        except Exception as e:
             logger.error(f"Error during output formatting: {e}", exc_info=True)
             print(f"\nERROR during output formatting: {e}")
    else:
        print("  No scripts available to format.")


    # --- 7. Completion ---
    print_header("✅ NARRATIVE-CORE PIPELINE COMPLETE ✅")
    print("Check the 'pipeline_output' directory for detailed results.")


# --- Run the async function ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Narrative-Core E2E Pipeline")
    parser.add_argument("-e", "--episodes", type=int, help="Override the target number of episodes (e.g., 3)")
    args = parser.parse_args()

    # ... (API Key check remains the same) ...
    if not settings.OPENAI_API_KEY:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ERROR: OPENAI_API_KEY is not set in .env file. !!!")
        print("!!! Please create a .env file in the project root  !!!")
        print("!!! and add: OPENAI_API_KEY='sk-your-key-here'     !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        sys.exit(1)

    print("="*60)
    print("🚨 IMPORTANT: Ensure you have run 'python scripts/populate_rag_db.py' at least once!")
    print("="*60)
    print("NOTE: This script will run the full story generation pipeline.")
    print("      It starts with an interactive CLI for the story concept.")
    print("      It will make multiple API calls to OpenAI.")
    print("      Generated files will be saved in 'pipeline_output'.")
    input("Press Enter to start the pipeline...")

    try:
        asyncio.run(run_full_pipeline(args))
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user.")
    except Exception as main_err:
         logger.critical(f"Unhandled exception in main pipeline execution: {main_err}", exc_info=True)
         print(f"\n\nFATAL PIPELINE ERROR: {main_err}")
         print("Check logs and traceback for details.")