# Narrative-Core

In a world where the demand for engaging and immersive content is ever increasing, This project aims to stands as a revolutionary AI-driven storytelling system designed to transform brief ideas into rich, consistent multi-episode narratives with meaningful cultural elements.


Following are the problems we wish to tackle through this project :
- Narrative Coherence: The audience is frustrated with plot lines and points that don't go anywhere, weird and inconsistent behaviour of characters across episodes , no emotional depth in the story, minimal character development.

- Cultural Relevance: Incorporating traditional storytelling patterns like Panchatantra frameworks and Ashtarasa emotional arcs for authentic cultural resonance.

- Extended Narratives: Context window limitation in using AI based solution to scale production and cater to the rising demand. Sophisticated contextual compression techniques overcome token limitations, enabling truly expansive storytelling.

## Key Features ✨

Narrative-Core tackles these challenges with a modular, AI-powered pipeline:

*   **Intelligent Input Processing:** Accepts brief inputs via interactive CLI, using NLP to analyze concepts, classify genres, and detect cultural context (including RAG with relevant narrative databases).
*   **Automated Story Blueprinting:** Generates structured plot arcs (e.g., Three-Act) based on the concept and maps them into logical episode outlines. Builds a narrative knowledge graph (using NetworkX for prototype) to track entities and relationships.
*   **Consistent Character System:** Creates rich character profiles from basic input (Character Genesis), maintains semantic memory (vector store), manages relationships, and generates character-specific dialogue reflecting personality, state, and memory.
*   **Advanced Memory Management:** Employs hierarchical summarization (scene, episode, act levels) and context optimization to provide LLMs with the most relevant information while respecting token limits, ensuring continuity in long narratives.
*   **Multi-Episode Script Generation:** Constructs detailed scenes based on outlines and generates dialogue through character-specific prompting, assembling full episode scripts.
*   **Quality Control:** Includes automated checks for narrative coherence (plot logic, character consistency) and cultural validity/sensitivity using LLM-based validation.
*   **Flexible Output Formatting:** Adapts generated scripts into various formats, including plain text, SSML for audio production, and structured metadata (summaries, keywords, content warnings).

### Developers :
> [Vaibhav Gupta](https://github.com/kvaibhav23/), [Vaibhav Itauriya](https://github.com/vaibhav-itauriya), [Krishna Agrawal](https://github.com/krishnaag23/)
