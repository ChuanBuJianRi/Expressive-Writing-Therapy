"""Configuration from environment variables."""
import os


class Config:
    # Primary LLM
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o")

    # IBM watsonx.ai
    WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
    WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
    WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    # Boost / Fallback LLM
    LLM_BOOST_API_KEY = os.getenv("LLM_BOOST_API_KEY", "")
    LLM_BOOST_BASE_URL = os.getenv("LLM_BOOST_BASE_URL", "")
    LLM_BOOST_MODEL_NAME = os.getenv("LLM_BOOST_MODEL_NAME", "")

    # Server
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5001))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
