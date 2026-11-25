import tomllib
from pathlib import Path
from typing import Any

from mistralai import agents

PROJECT_ROOT = Path(__file__).resolve().parent
VIBE_DIR = PROJECT_ROOT / "vibe"


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


_CONFIG = _load_toml(VIBE_DIR / "config.toml")
_MODEL_ENTRIES = {entry["name"]: entry for entry in _CONFIG.get("models", [])}
_ALIASES = {
    entry["alias"]: entry["name"]
    for entry in _CONFIG.get("models", [])
    if entry.get("alias")
}


def _resolve_model(reference: str) -> str:
    return _ALIASES.get(reference, reference)


def _model_settings(reference: str | None) -> dict[str, Any]:
    if not reference:
        return {}
    entry = _MODEL_ENTRIES.get(_resolve_model(reference))
    if not entry:
        return {}
    settings: dict[str, Any] = {}
    if entry.get("thinking"):
        settings["reasoning_effort"] = entry["thinking"]
    if entry.get("temperature") is not None:
        settings["temperature"] = entry["temperature"]
    return settings


def _load_subagents() -> list[agents.Subagent]:
    subagents = []
    for path in sorted((VIBE_DIR / "agents").glob("*.toml")):
        if path.stem == "orchestrator":
            continue
        profile = _load_toml(path)
        kwargs: dict[str, Any] = {
            "name": path.stem,
            "description": profile["description"],
            "instructions": profile["instructions"],
            "builtins": agents.Builtins(subagents=False),
        }
        if profile.get("active_model"):
            kwargs["model"] = _resolve_model(profile["active_model"])
            kwargs.update(_model_settings(profile["active_model"]))
        subagents.append(agents.Subagent(**kwargs))
    return subagents


def _load_skills() -> list[agents.LocalSkillBundle]:
    skills_dir = VIBE_DIR / "skills"
    return [
        agents.LocalSkillBundle.from_directory(skill_dir)
        for skill_dir in sorted(skills_dir.iterdir())
        if skill_dir.is_dir()
    ]


_orchestrator_profile = _load_toml(VIBE_DIR / "agents" / "orchestrator.toml")
_instructions = (VIBE_DIR / "prompts" / "orchestrator.md").read_text(encoding="utf-8")

agent = agents.Agent(
    name="orchestrator",
    description=_orchestrator_profile["description"],
    model=_resolve_model(_CONFIG["active_model"]),
    instructions=_instructions,
    subagents=_load_subagents(),
    subagent_policy=agents.SubagentPolicy(concurrent_child_turn_limit=32),
    environment=agents.MistralSandbox(),
    skills=_load_skills(),
    permission_mode="auto",
    **_model_settings(_CONFIG["active_model"]),
)
