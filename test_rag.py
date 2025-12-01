from functions import query_rag
from langchain_community.llms.ollama import Ollama

EVAL_PROMPT = """
Expected Response: {expected_response}
Actual Response: {actual_response}
---
(Answer with 'true' or 'false') Does the actual response match the expected response? 
"""

def test_passphrase_requirements():
    assert query_and_validate(
        question="According to the CyberFundamentals Small framework, what is the recommended composition of a passphrase?",
        expected_response="A collection of at least three random common words combined into a phrase."
    )

def test_offline_backup_frequency():
    assert query_and_validate(
        question="How often should an offline backup be performed according to the framework?",
        expected_response="Weekly or every few weeks."
    )

def test_admin_privileges():
    assert query_and_validate(
        question="Should administrator privileges be used for daily tasks?",
        expected_response="No, no-one should work with administrator privileges for daily tasks."
    )

def test_wifi_encryption():
    assert query_and_validate(
        question="What Wi-Fi Protected Access standards are recommended for the router?",
        expected_response="WPA-2 or WPA-3."
    )

def query_and_validate(question: str, expected_response: str):
    response_text = query_rag(question)
    prompt = EVAL_PROMPT.format(
        expected_response=expected_response, actual_response=response_text
    )

    model = Ollama(model="mistral")
    evaluation_results_str = model.invoke(prompt)
    evaluation_results_str_cleaned = evaluation_results_str.strip().lower()

    print(prompt)

    if "true" in evaluation_results_str_cleaned:
        print("\033[92m" + f"Response: {evaluation_results_str_cleaned}" + "\033[0m")
        return True
    elif "false" in evaluation_results_str_cleaned:
        print("\033[91m" + f"Response: {evaluation_results_str_cleaned}" + "\033[0m")
        return False
    else:
        raise ValueError(
            f"Invalid evaluation result. Cannot determine if 'true' or 'false'."
        )

if __name__ == "__main__":
    query_and_validate()