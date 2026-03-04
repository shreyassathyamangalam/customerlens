"""
config/settings.py
===================
Central configuration — reads from environment variables / .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Neo4j AuraDB
    neo4j_uri: str = "neo4j+s://localhost:7687"
    neo4j_username: str = ""
    neo4j_password: str = ""

    # Anthropic
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-5"

    # Data generation
    num_customers: int = 500
    num_products: int = 200
    num_orders: int = 2000
    random_seed: int = 42


settings = Settings()
