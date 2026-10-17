"""Small helper kit shared by the chapter scripts.

kit.db    - connect to ArangoDB, create collections / graphs / indexes / views
kit.llm   - chat, JSON chat, structured outputs and embeddings (OpenAI-compatible)
kit.text  - chunking, token counting, safe document keys
"""
try:  # load code/.env if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass
