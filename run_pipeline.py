#!/usr/bin/env python

import asyncio
import sys
import os
import logging
import json
import argparse # For command-line arguments
from typing import Optional, Dict, Any, List
from pydantic import ValidationError

# --- Define Node/Rel Types ---
NODE_CHARACTER = "Character"
NODE_LOCATION = "Location"
NODE_EVENT = "Event"
NODE_EPISODE = "Episode"
NODE_THEME = "Theme"
NODE_OBJECT = "Object"
NODE_PLOT_POINT = "PlotPoint"
REL_INTERACTS_WITH = "INTERACTS_WITH"
REL_LOCATED_IN = "LOCATED_IN"
REL_PART_OF = "PART_OF"
REL_HAS_TRAIT = "HAS_TRAIT"
REL_HAS_GOAL = "HAS_GOAL"
REL_AFFECTS = "AFFECTS"
REL_MENTIONS = "MENTIONS"
REL_LEADS_TO = "LEADS_TO"
REL_CONTAINS = "CONTAINS"
REL_INVOLVES = "INVOLVES"
REL_ADVANCES = "ADVANCES"
REL_FOLLOWS = "FOLLOWS"


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

    # Input Processing Components (Needed for processing JSON input)
    from src.input_processing.nlp_analyser import NlpAnalyzer
    from src.input_processing.genre_classifier import GenreClassifier
    from src.input_processing.cultural_context_detector import CulturalContextDetector
    from src.input_processing.story_elements import (
        StoryConcept, CharacterInput, SettingInput, PlotInput, GenreAnalysis,
        CulturalAnalysis, NLPExtraction, TargetAudience, StoryLength,
        CharacterRole, ConflictType, StoryTone
    )

    # Other Core Components / Facades
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
# Logging level is set globally by config.py based on LOG_LEVEL in .env or default
logger = logging.getLogger("NarrativeCorePipeline")


# --- Helper Functions ---
def get_target_episode_count(length_enum_str: str, override: Optional[int] = None) -> int:
    """Maps StoryLength string or uses override to get episode count."""
    if override is not None and override > 0:
        logger.info(f"Using episode count override: {override}")
        return override

    # Map the string value from StoryConcept back to enum if needed, or compare strings
    # Comparing string values directly for simplicity here
    length_map = {
        StoryLength.SHORT: 2, # Shortened for faster demo
        StoryLength.MEDIUM: 4, # Shortened for faster demo
        StoryLength.LONG: 6,  # Shortened for faster demo
    }
    default_count = 3 # Default if mapping fails or value is unexpected
    count = length_map.get(length_enum_str, default_count)
    logger.info(f"Determined target episode count: {count} (based on '{length_enum_str}')")
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
    """Executes the complete Narrative-Core generation pipeline from a JSON input file."""
    print_header("🚀 STARTING NARRATIVE-CORE PIPELINE (JSON Input) 🚀")

    # --- 0. Initialization ---
    print_subheader("Initializing Core Components")
    try:
        llm_wrapper = LLMwrapper()
        vector_store = VectorStoreInterface() # RAG DB should be populated before running this
        prompt_manager = PromptManager()
        graph_db_instance = GraphDB()

        # Initialize analyzers needed for processing JSON input
        nlp_analyzer = NlpAnalyzer()
        genre_classifier = GenreClassifier()
        cultural_detector = CulturalContextDetector(vector_store=vector_store) # Pass vector store for RAG

        # Facades and Managers
        character_facade = CharacterSystemFacade(llm_wrapper=llm_wrapper)
        summarizer = HierarchicalSummarizer(llm_wrapper=llm_wrapper)
        kg_manager = KnowledgeGraphManager()
        context_optimizer = ContextOptimizer(
            llm_wrapper=llm_wrapper, summarizer=summarizer, kg_manager=kg_manager,
            character_memory=character_facade.memory_manager
        )
        plot_arc_generator = PlotArcGenerator(llm_wrapper=llm_wrapper)
        episode_mapper = EpisodeMapper(llm_wrapper=llm_wrapper) # LLM needed for refinement
        narrative_graph_builder = NarrativeGraphBuilder()
        script_builder = ScriptBuilder(llm_wrapper=llm_wrapper, character_facade=character_facade)
        qc_facade = QualityControlFacade(llm_wrapper=llm_wrapper)
        metadata_generator = MetadataGenerator(llm_wrapper=llm_wrapper)
        audio_adapter = AudioAdapter()

        print("Core components initialized successfully.")
        print(f"LLM Model: {settings.LLM_MODEL_NAME}")
        print(f"Vector DB Path: {settings.VECTOR_DB_PATH}")
        print(f"Verbose Context: {settings.DEMO_VERBOSE_CONTEXT}")
        print("NOTE: Ensure 'scripts/populate_rag_db.py' has been run at least once!")

    except Exception as e:
        logger.critical(f"Failed during component initialization: {e}", exc_info=True)
        print(f"\nFATAL ERROR: Could not initialize core components: {e}")
        return

    # --- 1. Input Processing ---
    print_header("Stage 1: Input Processing (From JSON File)")
    story_concept: Optional[StoryConcept] = None
    raw_input_data: Optional[Dict] = None

    try:
        # Load data from JSON file specified by argument
        input_file_path = args.input_file
        print(f"Loading input data from: {input_file_path}")
        if not os.path.exists(input_file_path):
            raise FileNotFoundError(f"Input file not found: {input_file_path}")

        with open(input_file_path, 'r', encoding='utf-8') as f:
            raw_input_data = json.load(f)
        print("Input data loaded successfully.")

        # --- Replicate Analysis Logic from ConceptBuilder ---
        concept_note = raw_input_data.get("concept_note")
        genre_hint = raw_input_data.get("genre_hint")

        # NLP Analysis
        print("  Running NLP Analysis...")
        nlp_analysis: Optional[NLPExtraction] = nlp_analyzer.analyze_text(concept_note)
        print(f"    NLP Entities Found: {len(nlp_analysis.extracted_entities) if nlp_analysis else 0}")

        # Genre Classification
        print("  Running Genre Classification...")
        genre_analysis_result: Optional[GenreAnalysis] = genre_classifier.classify(
            text_input=concept_note,
            genre_hint=genre_hint
        )
        if not genre_analysis_result:
             logger.warning("Genre classification failed. Using defaults.")
             genre_analysis_result = GenreAnalysis(primary_genre=("Unknown", 0.0), secondary_genres=[], genre_specific_prompts={}) # Ensure default
        print(f"    Primary Genre Classified: {genre_analysis_result.primary_genre[0]}")

        # Cultural Context Analysis (including RAG)
        print("  Running Cultural Context Analysis (Keywords + RAG)...")
        text_for_cultural_analysis = [
            concept_note,
            raw_input_data.get("setting", {}).get("cultural_context_notes"),
            raw_input_data.get("setting", {}).get("location"),
            ", ".join(raw_input_data.get("plot", {}).get("potential_themes", [])),
        ]
        cultural_analysis: CulturalAnalysis = cultural_detector.analyze(
            [text for text in text_for_cultural_analysis if text]
        )
        print(f"    Cultural Keywords Detected: {cultural_analysis.detected_keywords or 'None'}")
        print(f"    Frameworks Suggested: {cultural_analysis.suggested_frameworks or 'None'}")

        # Structure and Validate the Final Concept
        print("  Structuring and validating final StoryConcept...")
        plot_raw = raw_input_data.get("plot", {})
        setting_raw = raw_input_data.get("setting", {})
        characters_raw = raw_input_data.get("characters", [])

        # Need to handle potential Enum mismatches if JSON uses strings
        # Pydantic usually handles this during validation if Config.use_enum_values=True (default)
        story_concept = StoryConcept(
            title_suggestion=raw_input_data.get("title_suggestion"),
            target_audience=raw_input_data.get("target_audience", TargetAudience.ADULTS),
            story_length=raw_input_data.get("story_length", StoryLength.MEDIUM),
            initial_characters=[CharacterInput(**char_data) for char_data in characters_raw],
            initial_setting=SettingInput(
                time_period=setting_raw.get("time_period", "Undefined"),
                location=setting_raw.get("location", "Undefined"),
                atmosphere=setting_raw.get("atmosphere"),
                cultural_context_notes=setting_raw.get("cultural_context_notes")
            ),
            initial_plot=PlotInput(
                logline=plot_raw.get("logline"),
                concept_note=concept_note, # Use the loaded concept note
                primary_conflict=plot_raw.get("primary_conflict", ConflictType.PERSON_VS_PERSON),
                major_plot_points=plot_raw.get("major_plot_points", []),
                potential_themes=plot_raw.get("potential_themes", []),
                desired_tone=plot_raw.get("desired_tone", StoryTone.DARK_SERIOUS)
            ),
            genre_analysis=genre_analysis_result,
            cultural_analysis=cultural_analysis,
            nlp_analysis=nlp_analysis,
            # Flags need to be generated based on analysis results
            processing_flags=cultural_detector._generate_processing_flags(cultural_analysis, genre_analysis_result) if hasattr(cultural_detector, '_generate_processing_flags') else {}, # Generate flags if method exists
            generation_metadata=raw_input_data.get("metadata", {"input_mode": "json_file"})
        )
        print("  StoryConcept validated successfully.")

    except FileNotFoundError as e:
        logger.error(f"Input file error: {e}")
        print(f"\nERROR: {e}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in input file '{args.input_file}': {e}")
        print(f"\nERROR: Could not parse JSON input file '{args.input_file}'. Check its format.")
        return
    except ValidationError as e:
         logger.error(f"Failed to validate StoryConcept from JSON data: {e}", exc_info=True)
         print(f"\nERROR: Input data validation failed. Details:\n{e}")
         return
    except Exception as e:
        logger.error(f"Error during input processing from JSON: {e}", exc_info=True)
        print(f"\nERROR during input processing: {e}")
        return

    # --- Print Concept Summary (Moved after successful creation) ---
    print("\n--- Input Processing Complete ---")
    print(f"  Title Suggestion: {story_concept.title_suggestion or 'N/A'}")
    print(f"  Primary Genre: {story_concept.genre_analysis.primary_genre[0]} (Score: {story_concept.genre_analysis.primary_genre[1]:.2f})")
    print(f"  Target Audience: {story_concept.target_audience}") # Use .value for enum string
    print(f"  Story Length: {story_concept.story_length}") # Use .value for enum string
    print(f"  Characters Input: {len(story_concept.initial_characters)}")
    # Cultural info printed during analysis phase above
    await save_output("1_story_concept.json", story_concept.model_dump(), is_json=True)
    print("  (Full concept saved to pipeline_output/1_story_concept.json)")

    # --- Stage 2: Character Genesis ---
    print_header("Stage 2: Character Genesis")
    generated_profiles_dict: Dict[str, CharacterProfile] = {} # Store by name
    if not story_concept.initial_characters:
        print("No initial characters found in concept.")
    else:
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

    # --- Stage 3: Story Blueprint ---
    print_header("Stage 3: Story Blueprint (Arc, Mapping, Graph)")
    plot_arc_data: Optional[Dict[str, Any]] = None
    episode_outlines: List[Dict[str, Any]] = []
    target_ep_count = get_target_episode_count(story_concept.story_length, args.episodes)

    try:
        print_subheader("Building Initial Knowledge Graph")
        narrative_graph_builder
        print("  Initial graph nodes (Characters, Location, Themes) added.")

        print_subheader("Generating Plot Arc")
        plot_arc_data = await plot_arc_generator.generate_arc(story_concept)
        if not plot_arc_data or ("plot_arc" not in plot_arc_data and "raw_llm_output" not in plot_arc_data):
            print("  ❌ Plot arc generation failed (No LLM response or invalid data).")
            return # Cannot proceed without plot arc

        if "raw_llm_output" in plot_arc_data:
            print("  ❌ Plot arc generation failed to produce valid JSON. Raw output saved.")
            await save_output("3a_plot_arc_raw_error.txt", plot_arc_data["raw_llm_output"])
            return # Cannot proceed reliably

        print(f"  ✅ Plot arc generated with {len(plot_arc_data.get('plot_arc',[]))} stages.")
        for i, stage in enumerate(plot_arc_data.get('plot_arc', [])):
            print(f"     Stage {i+1}: {stage.get('stage_name')} - Points: {len(stage.get('plot_points', []))}")
        await save_output("3a_plot_arc.json", plot_arc_data, is_json=True)

        print_subheader("Adding Plot Arc to Knowledge Graph")
        narrative_graph_builder.add_plot_arc_to_graph(plot_arc_data, story_concept)
        print("  Plot points and relationships added to graph.")

        print_subheader("Mapping Arc to Episodes")
        # Ensure episode_mapper gets initialized PlotArcGenerator, if needed
        episode_outlines = episode_mapper.map_plot_to_episodes(plot_arc_data, target_ep_count)
        if not episode_outlines:
             print("  ❌ Episode mapping failed.")
             return
        print(f"  ✅ Mapped into {len(episode_outlines)} episode outlines.")
        await save_output("3b_episode_outlines.json", episode_outlines, is_json=True)

        print_subheader("Adding Episode Structure to Knowledge Graph")
        narrative_graph_builder.add_episode_structure_to_graph(episode_outlines)
        print("  Episode nodes linked to plot points in graph.")

        # Attempt Visualization (remains the same)
        print_subheader("Visualizing Knowledge Graph (Attempt)")
        try:
             graph_obj = narrative_graph_builder.get_graph()
             if graph_obj and graph_obj.number_of_nodes() > 0:
                  import matplotlib.pyplot as plt
                  import networkx as nx
                  plt.figure(figsize=(15, 10))
                  pos = nx.spring_layout(graph_obj, k=0.3, iterations=50)
                  node_colors = []
                  node_labels = {}
                  for node, data in graph_obj.nodes(data=True):
                       node_type = data.get('type', 'Unknown')
                       node_labels[node] = f"{node}\n({node_type})"
                       if node_type == NODE_CHARACTER: node_colors.append('skyblue')
                       elif node_type == NODE_LOCATION: node_colors.append('lightgreen')
                       elif node_type == NODE_EPISODE: node_colors.append('salmon')
                       elif node_type == NODE_PLOT_POINT: node_colors.append('lightcoral')
                       elif node_type == NODE_THEME: node_colors.append('gold')
                       else: node_colors.append('grey')

                  nx.draw(graph_obj, pos, labels=node_labels, node_color=node_colors, with_labels=True,
                          node_size=2000, font_size=8, alpha=0.8, edge_color='gray')
                  graph_img_path = os.path.join(PROJECT_ROOT, "pipeline_output", "3c_narrative_graph.png")
                  plt.title("Narrative Knowledge Graph")
                  plt.savefig(graph_img_path)
                  plt.close()
                  print(f"  ✅ Graph visualization saved to: {graph_img_path}")
             else:
                  print("  Graph is empty, skipping visualization.")
             if graph_obj:
                  nx.write_gml(graph_obj, os.path.join(PROJECT_ROOT, "pipeline_output", "3c_narrative_graph.gml"))
                  print("  (Graph data also saved to pipeline_output/3c_narrative_graph.gml)")

        except ImportError:
             logger.warning("Matplotlib or NetworkX not found. Cannot visualize graph.")
             print("  Skipping graph visualization (matplotlib/networkx not installed).")
        except Exception as graph_err:
             logger.warning(f"Could not visualize or save narrative graph: {graph_err}")
             print(f"  Graph visualization/saving failed: {graph_err}")

    except Exception as e:
        logger.error(f"Error during story blueprinting: {e}", exc_info=True)
        print(f"\nERROR during story blueprinting: {e}")
        return


    # --- Stage 4: Episode Generation ---
    print_header("Stage 4: Episode Generation")
    generated_scripts: List[Dict[str, Any]] = []
    episode_summaries_for_qc: Dict[int, str] = {}

    print(f"Generating scripts for {len(episode_outlines)} episodes...")
    # Run sequentially for simplicity, could be parallelized with care
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
                print("     Script Snippet (First Scene Start):")
                if final_script.get("scenes"):
                     first_scene_elements = final_script["scenes"][0].get("elements", [])[:3]
                     for el in first_scene_elements:
                          print(f"       - {el.get('type', '')}: {str(el.get('content', ''))[:80]}...")
                await save_output(f"4_episode_{ep_num}_script.json", final_script, is_json=True)

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

    if len(generated_scripts) != len(episode_outlines):
        print(f"\nWarning: Only {len(generated_scripts)} out of {len(episode_outlines)} episodes were generated successfully.")
    if not generated_scripts:
         print("\nNo episode scripts were generated. Cannot proceed.")
         return
    print("  (Full episode scripts saved to pipeline_output/4_episode_*_script.json)")


    # --- Stage 5: Quality Control ---
    print_header("Stage 5: Quality Control")
    quality_report: Optional[QualityReport] = None
    try:
        print("  Running automated quality checks...")
        profiles_by_id = {p.character_id: p for p in generated_profiles_dict.values()}
        quality_report = await qc_facade.run_all_checks(
            story_concept=story_concept,
            # Add generated summaries to the episode data for QC checks
            generated_episodes=[{**script, "summary": episode_summaries_for_qc.get(script.get("episode_number"))} for script in generated_scripts],
            character_profiles=profiles_by_id
        )
        if quality_report:
             print(f"  ✅ Quality Check Complete - Score: {quality_report.overall_score:.2f}, Passed: {quality_report.passed}")
             print(f"  Number of Issues Found: {len(quality_report.issues)}")
             if quality_report.issues:
                  print("  Issues:")
                  for issue in quality_report.issues[:5]:
                       # Use .value for enum severity
                       print(f"    - [{issue.severity.value} / {issue.checker} / {issue.check_type}] {issue.description} (Loc: {issue.location or 'N/A'})")
                  if len(quality_report.issues) > 5: print("      ...")
             await save_output("5_quality_report.json", quality_report.model_dump(), is_json=True)
             print("  (Full quality report saved to pipeline_output/5_quality_report.json)")
        else:
            print("  ❌ Quality check failed to produce a report.")

    except Exception as e:
        logger.error(f"Error during quality control checks: {e}", exc_info=True)
        print(f"\nERROR during quality control: {e}")

    # --- Stage 6: Output Formatting ---
    print_header("Stage 6: Output Formatting")
    print("  Generating metadata and audio format for Episode 1...")
    if generated_scripts:
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
    parser = argparse.ArgumentParser(description="Run the Narrative-Core E2E Pipeline from a JSON file.")
    parser.add_argument(
        "-i", "--input-file",
        default="sample_input.json", # Default to sample_input.json in root
        help="Path to the JSON file containing the story concept input (default: sample_input.json)"
    )
    parser.add_argument("-e", "--episodes", type=int, help="Override the target number of episodes (e.g., 3)")
    args = parser.parse_args()

    # --- API Key Check ---
    if not settings.OPENAI_API_KEY:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ERROR: OPENAI_API_KEY is not set in .env file. !!!")
        print("!!! Please create a .env file in the project root  !!!")
        print("!!! and add: OPENAI_API_KEY='sk-your-key-here'     !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        sys.exit(1)

    # --- Pre-run Checks and Info ---
    print("="*60)
    print("🚨 IMPORTANT: Ensure you have run 'python scripts/populate_rag_db.py' at least once!")
    print("="*60)
    print(f"Attempting to load input from: {args.input_file}")
    if not os.path.exists(args.input_file):
         print(f"ERROR: Input file '{args.input_file}' not found.")
         print("Please create the JSON input file or specify the correct path using --input-file.")
         sys.exit(1)

    print("\nNOTE: This script will run the full story generation pipeline.")
    print("      It reads input from the specified JSON file.")
    print("      It will make multiple API calls to OpenAI.")
    print("      Generated files will be saved in 'pipeline_output'.")
    input("Press Enter to start the pipeline...") # Keep confirmation for safety

    # --- Execute Pipeline ---
    try:
        asyncio.run(run_full_pipeline(args))
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user.")
    except Exception as main_err:
         logger.critical(f"Unhandled exception in main pipeline execution: {main_err}", exc_info=True)
         print(f"\n\nFATAL PIPELINE ERROR: {main_err}")
         print("Check logs and traceback for details.")