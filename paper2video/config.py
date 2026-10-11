"""Load project configuration without exposing credentials."""
from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    base_url: str
    model: str
    review_model: str
    timeout_seconds: int
    tts_voice: str
    target_duration_seconds: int
    font_path: Path | None
    output_dir: Path

    def require_llm(self) -> None:
        if not self.api_key.strip():
            raise ValueError("缺少 LLM_API_KEY，请在 .env 或环境变量中设置；不要把密钥发到聊天里。")


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    duration = int(os.getenv("TARGET_DURATION_SECONDS", "600"))
    if timeout <= 0 or duration <= 0:
        raise ValueError("超时和目标时长必须为正整数。")
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
    if not base_url.startswith("https://"):
        raise ValueError("LLM_BASE_URL 必须使用 HTTPS。")
    font = os.getenv("FONT_PATH", "").strip()
    return Settings(
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=base_url,
        model=os.getenv("LLM_MODEL", "deepseek-chat"),
        review_model=os.getenv("REVIEW_MODEL", "deepseek-reasoner"),
        timeout_seconds=timeout,
        tts_voice=os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural"),
        target_duration_seconds=duration,
        font_path=Path(font).expanduser() if font else None,
        output_dir=PROJECT_ROOT / "output",
    )


if __name__ == "__main__":
    settings = load_settings()
    print(f"模型：{settings.model}；API 密钥：{'已配置' if settings.api_key else '未配置'}")
    print(f"目标时长：{settings.target_duration_seconds} 秒")
