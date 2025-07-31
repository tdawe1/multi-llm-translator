import json
import pytest
from translators.utils import load_glossary
import config # Import the whole module so we can patch it

def test_load_glossary_success(tmp_path, monkeypatch):
    """Tests that the glossary loads correctly from a valid file."""
    # 1. Create a temporary glossary file for the test
    glossary_file = tmp_path / "glossary.json"
    glossary_data = {"Hello": "Bonjour"}
    glossary_file.write_text(json.dumps(glossary_data))
    
    # 2. Use monkeypatch to temporarily set the GLOSSARY_PATH in the config module
    # This change will be seen by all other modules, including translators.utils
    monkeypatch.setattr(config, "GLOSSARY_PATH", str(glossary_file))
    
    # 3. Run the function and assert the result
    assert load_glossary() == glossary_data

def test_load_glossary_not_found(monkeypatch):
    """Tests that it returns an empty dict if the file doesn't exist."""
    # 1. Use monkeypatch to point to a file that does not exist
    monkeypatch.setattr(config, "GLOSSARY_PATH", "non_existent_file.json")

    # 2. Run the function and assert that it returns an empty dictionary
    assert load_glossary() == {}

def test_load_glossary_bad_json(tmp_path, monkeypatch):
    """Tests that it returns an empty dict if the JSON is invalid."""
    # 1. Create a file with malformed JSON
    bad_json_file = tmp_path / "bad_glossary.json"
    bad_json_file.write_text("{'key': 'value',}") # Invalid JSON with trailing comma and single quotes
    
    # 2. Use monkeypatch to point to the bad file
    monkeypatch.setattr(config, "GLOSSARY_PATH", str(bad_json_file))
    
    # 3. Assert that the function handles the error and returns an empty dict
    assert load_glossary() == {}
