from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    app_title: str
    default_tenant_id: str
    timeout_seconds: int
    workiq_path: str


def get_settings() -> Settings:
    return Settings(
        app_title=os.getenv("APP_TITLE", "WorkIQ Showcase"),
        default_tenant_id=os.getenv("WORKIQ_TENANT_ID", "").strip(),
        timeout_seconds=int(os.getenv("WORKIQ_TIMEOUT_SECONDS", "120")),
        workiq_path=os.getenv("WORKIQ_PATH", "").strip(),
    )