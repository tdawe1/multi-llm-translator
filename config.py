from dotenv import load_dotenv
import os

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Operation Mode
OPERATION_MODE = os.getenv("OPERATION_MODE", "PARALLEL").upper()
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "gpt").lower()

# Glossary
GLOSSARY_PATH = os.getenv("GLOSSARY_PATH", "glossary.json")

# Language Defaults
DEFAULT_SOURCE_LANGUAGE = "Japanese"
DEFAULT_TARGET_LANGUAGE = "English"

# Dummy Mode
DUMMY_MODE = os.getenv("DUMMY_MODE", "False").upper() == 'TRUE'