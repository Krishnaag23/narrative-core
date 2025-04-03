"""
Formats episode scripts for audio production, generating formats like
plain text dialogue or SSML.
"""
import logging
from typing import List, Dict, Any
from enum import Enum
import html # For escaping in SSML

logger = logging.getLogger(__name__)

class AudioFormat(Enum):
    SIMPLE_TEXT = "simple_text"
    SSML = "ssml"
    # TODO: Add other formats like JSON_AUDIO_SCRIPT etc.

class AudioAdapter:
    """Converts internal script representation to audio-friendly formats."""

    def format_for_audio(
        self,
        episode_script_elements: List[Dict[str, Any]],
        format_type: AudioFormat = AudioFormat.SIMPLE_TEXT
    ) -> str:
        """
        Formats the script elements based on the specified audio format.

        Args:
            episode_script_elements: A list of dictionaries representing script elements
                                     (e.g., {'type': 'dialogue', 'character': 'Name', 'content': '...'})
            format_type: The desired output format (AudioFormat enum).

        Returns:
            The formatted string.
        """
        logger.info(f"Formatting script for audio - Format: {format_type.value}")
        if format_type == AudioFormat.SSML:
            return self._to_ssml(episode_script_elements)
        elif format_type == AudioFormat.SIMPLE_TEXT:
            return self._to_simple_dialogue(episode_script_elements)
        else:
            logger.warning(f"Unsupported audio format requested: {format_type}. Defaulting to simple text.")
            return self._to_simple_dialogue(episode_script_elements)

    def _escape_ssml(self, text: str) -> str:
        """Escapes characters that are special in SSML/XML."""
        return html.escape(text, quote=True)

    def _to_ssml(self, elements: List[Dict[str, Any]]) -> str:
        """Converts script elements to SSML format."""
        ssml_parts = ['<speak xmlns="http://www.w3.org/2001/10/synthesis" version="1.0" xml:lang="en-US">'] # TODO: Make lang configurable

        for element in elements:
            el_type = element.get("type")
            content = element.get("content")
            character = element.get("character")

            if not content:
                continue

            escaped_content = self._escape_ssml(content)

            if el_type == "dialogue" and character:
                # Basic paragraph per dialogue line. Could add <voice name="..."> based on character profile later.
                ssml_parts.append(f'  <p><s>{self._escape_ssml(character)}: {escaped_content}</s></p>')
            elif el_type == "narration":
                 # Could use a different voice or prosody for narrator
                 ssml_parts.append(f'  <p><s>{escaped_content}</s></p>')
            elif el_type == "description" or el_type == "action":
                 # Represent actions/descriptions as pauses or non-verbal cues if needed
                 # For basic SSML, often omitted or added as comments if the processor supports it.
                 # Adding a short break for pacing.
                 ssml_parts.append('  <break time="500ms"/>') # Pause for action/description
                 # Optionally add as comment if supported: <!-- Action: escaped_content -->
            elif el_type == "sound":
                 # SSML has <audio> tag for sound effects, but requires src URL.
                 # Add as comment or short break.
                 ssml_parts.append(f'  <break time="200ms"/> <!-- Sound: {escaped_content} -->')

        ssml_parts.append('</speak>')
        return "\n".join(ssml_parts)

    def _to_simple_dialogue(self, elements: List[Dict[str, Any]]) -> str:
        """Formats the script into simple 'Character: Dialogue' lines with actions."""
        output_lines = []
        for element in elements:
            el_type = element.get("type")
            content = element.get("content")
            character = element.get("character")

            if not content:
                continue

            if el_type == "dialogue" and character:
                output_lines.append(f"{character}: {content}")
            elif el_type == "narration":
                 output_lines.append(f"NARRATOR: {content}")
            elif el_type == "action":
                 output_lines.append(f"(ACTION: {content})")
            elif el_type == "description":
                 output_lines.append(f"(SCENE: {content})")
            elif el_type == "sound":
                 output_lines.append(f"(SOUND: {content})")

        return "\n".join(output_lines)