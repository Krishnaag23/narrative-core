Manages loading and formatting of prompt templates stored in YAML files.
Allows easy updates to prompts without changing core code.

 --- Example Usage ---

```
 prompt_manager = PromptManager()
 formatted_prompt = prompt_manager.get_prompt(
     "character_genesis_expand", # Assumes this key exists in a YAML file
     name="Arjun",
     role="Protagonist",
     description="A weary warrior",
     # ... other kwargs expected by the prompt template
 )
 if formatted_prompt:
     print(formatted_prompt)
```