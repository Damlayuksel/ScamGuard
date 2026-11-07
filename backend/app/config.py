from functools import lru_cache
from typing import Annotated, Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_PLACEHOLDER_SECRET = "change-me"  # noqa: S105 - placeholder from .env.example, rejected in prod


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    secret_key: SecretStr
    database_url: str
    redis_url: str

    # The old usom.gov.tr/url-list.txt now redirects here (paginated JSON API).
    usom_api_url: str = "https://siberguvenlik.gov.tr/api/address/index"
    urlhaus_url: str = "https://urlhaus.abuse.ch/downloads/text_online/"
    urlhaus_auth_key: SecretStr = SecretStr("")

    cors_origins: Annotated[list[str], NoDecode] = []
    trusted_proxies: Annotated[list[str], NoDecode] = ["127.0.0.1"]

    @field_validator("cors_origins", "trusted_proxies", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _check_production_secret(self) -> "Settings":
        if self.env == "prod":
            secret = self.secret_key.get_secret_value()
            if secret == _PLACEHOLDER_SECRET or len(secret) < 32:
                raise ValueError(
                    "SECRET_KEY must be a random value of at least 32 characters in prod"
                )
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.env != "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
