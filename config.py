from dotenv import load_dotenv
import os

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Dummy Mode Switch
DUMMY_MODE = os.getenv("DUMMY_MODE", "False").upper() == 'TRUE'