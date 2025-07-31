import json
import config
from translators.utils import get_prompt_with_glossary


def test_get_prompt_with_glossary(tmp_path, monkeypatch):
    """Tests that the glossary is correctly formatted and injected into a prompt template."""
    # 1. Create a fake prompt template file
    template_file = tmp_path / "prompt.txt"
    template_file.write_text("Instruction: {glossary_section}\n\nText: {text}")

    # 2. Create a fake glossary file
    glossary_file = tmp_path / "glossary.json"
    glossary_data = {"Gengo": "Gengo Inc.", "LLM": "Large Language Model"}
    glossary_file.write_text(json.dumps(glossary_data))

    # 3. Patch the config to use our fake glossary
    monkeypatch.setattr(config, "GLOSSARY_PATH", str(glossary_file))

    # 4. Define placeholders and call the function
    placeholders = {"{text}": "Translate this."}
    result_prompt = get_prompt_with_glossary(str(template_file), placeholders)

    # 5. Assert that the glossary terms are present in the final prompt
    assert "You must adhere to the following glossary terms:" in result_prompt
    assert '- "Gengo" must be translated as "Gengo Inc."' in result_prompt
    assert '- "LLM" must be translated as "Large Language Model"' in result_prompt
    assert "Text: Translate this." in result_prompt


def test_get_prompt_without_glossary(tmp_path, monkeypatch):
    """Tests that the glossary section is empty if the glossary file doesn't exist."""
    # 1. Create a fake prompt template file
    template_file = tmp_path / "prompt.txt"
    template_file.write_text("Instruction: {glossary_section}Text: {text}")

    # 2. Patch the config to point to a non-existent glossary
    monkeypatch.setattr(config, "GLOSSARY_PATH", "non_existent_glossary.json")

    # 3. Define placeholders and call the function
    placeholders = {"{text}": "Translate this."}
    result_prompt = get_prompt_with_glossary(str(template_file), placeholders)

    # 4. Assert that the glossary section is empty and the text is still there
    assert "Instruction: Text: Translate this." in result_prompt
    assert "You must adhere" not in result_prompt
