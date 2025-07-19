import os
import json
import traceback
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LLM_API_ENDPOINT = os.getenv("LLM_API_ENDPOINT", "https://dbasprdapi.samsungcloud.tv/chat/completions")

def get_completion(prompt: str, temperature: float = 1.0) -> str:
    """
    Get a completion from the local LLM.
    """
    detailed_prompt = f"""
    Analyze the following codebase and provide a detailed report.

    **Codebase:**
    ```
    {prompt}
    ```

    **Instructions:**

    1.  **High-Level Summary:** Provide a brief overview of the project's purpose and functionality.
    2.  **Package-Level Documentation:** For each package, describe its role and responsibilities.
    3.  **Class-Level Documentation:** For each class, explain its purpose, key methods, and collaborations with other classes.
    4.  **Function-Level Documentation:** For each function, describe its purpose, parameters, and return value.
    5.  **Utility Usage:** Identify and explain the key utilities and libraries used in the code.
    6.  **End-to-End Feature Flow:** Describe the end-to-end flow of a key feature, from the controller/API endpoint, through the service layer, to the repository/data access layer.
    7.  **Java AST Analysis:** Use your knowledge of Java Abstract Syntax Trees (AST) to provide a deep and accurate analysis of the code structure, identifying key patterns and potential areas for improvement.

    Please provide a comprehensive and well-structured response.
    """
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "llama3.3",
        "messages": [{"role": "user", "content": detailed_prompt}],
        "temperature": temperature,
        "stream": True,
    }

    try:
        response = requests.post(LLM_API_ENDPOINT, headers=headers, json=data, verify=False)
        return handle_streaming_response(response)
    except requests.exceptions.JSONDecodeError as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()

def handle_streaming_response(response) -> str:
    """
    Handle streaming response and concatenate all content chunks.
    """
    full_content = ""

    try:
        for line in response.iter_lines(decode_unicode=True):
            if line.strip():
                if line.startswith("data:"):
                    json_str = line[6:]
                    if json_str.strip() and json_str.strip() != "[DONE]":
                        try:
                            chunk = json.loads(json_str)
                            full_content += chunk["choices"][0]["delta"]["content"]
                        except (json.JSONDecodeError, KeyError):
                            # Ignore errors in streaming for now
                            pass
        print(f"\nFull concatenated response: '{full_content}'")
        return full_content.strip()
    except Exception as e:
        print(f"Error processing streaming response: {e}")
        return None
