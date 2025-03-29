
Utility functions and classes for interacting with Large Language Models (LLMs),
primarily focusing on the OpenAI API. Handles client initialization, requests,
and basic error handling.

 --- Example Usage ---
```
 async def main():
     prompt = "Tell me a short story about a robot who learns to paint."
     # Synchronous call
     sync_response = LLMUtils.query_llm_sync(prompt, max_tokens=99)
     if sync_response:
         print("Sync Response:", sync_response)

     # Asynchronous call
     async_response = await LLMUtils.query_llm_async(prompt, max_tokens=99, temperature=0.9)
     if async_response:
         print("Async Response:", async_response)

 if __name__ == "__main__":
      asyncio.run(main())
```