import tomllib
from pathlib import Path
from typing import Any

from mistralai import agents

PROJECT_ROOT = Path(__file__).resolve().parent

FALLBACK_MODEL = "mistral-large-4"
AVAILABLE_MODELS = frozenset(
    {
        "mistral-large-4-0",
        "deepseek-v4-1-flash-1017",
        "zai-glm-5-3",
        "zai-glm-5-3-flash",
        "mistral-small-latest",
    }
)


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _repo_relative(text: str) -> str:
    return text.replace("~/.vibe/", "./").replace("~/.vibe", ".")


_CONFIG = _load_toml(PROJECT_ROOT / "config.toml")
_MODEL_ENTRIES = {entry["name"]: entry for entry in _CONFIG.get("models", [])}
_ALIASES = {
    entry["alias"]: entry["name"]
    for entry in _CONFIG.get("models", [])
    if entry.get("alias")
}


def _resolve_model(reference: str) -> str:
    name = _ALIASES.get(reference, reference)
    if name not in AVAILABLE_MODELS:
        return FALLBACK_MODEL
    return name


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


def _bash_denylist() -> tuple[str, ...]:
    commands: list[str] = []
    for path in sorted((PROJECT_ROOT / "agents").glob("*.toml")):
        denylist = _load_toml(path).get("tools", {}).get("bash", {}).get("denylist", [])
        for command in denylist:
            if command not in commands:
                commands.append(command)
    return tuple(commands)


def _permission_policy() -> agents.PermissionPolicy:
    patterns = tuple(f'*\"command\": \"{command}\"*' for command in _bash_denylist())
    rule = agents.PermissionRule(
        tools=("file_system.bash",),
        decision="allow",
        denylist=patterns,
    )
    return agents.PermissionPolicy(default="allow", rules=(rule,))


def _load_subagents() -> list[agents.Subagent]:
    subagents = []
    for path in sorted((PROJECT_ROOT / "agents").glob("*.toml")):
        if path.stem == "orchestrator":
            continue
        profile = _load_toml(path)
        kwargs: dict[str, Any] = {
            "name": path.stem,
            "description": _repo_relative(profile["description"]),
            "instructions": _repo_relative(profile["instructions"]),
            "builtins": agents.Builtins(subagents=False),
        }
        enabled_tools = set(profile.get("enabled_tools", []))
        if not {"web_search", "web_fetch"} & enabled_tools:
            kwargs["connectors"] = []
        if profile.get("active_model"):
            kwargs["model"] = _resolve_model(profile["active_model"])
            kwargs.update(_model_settings(profile["active_model"]))
        subagents.append(agents.Subagent(**kwargs))
    return subagents


def _load_skills() -> list[agents.LocalSkillBundle]:
    skills_dir = PROJECT_ROOT / "skills"
    return [
        agents.LocalSkillBundle.from_directory(skill_dir)
        for skill_dir in sorted(skills_dir.iterdir())
        if skill_dir.is_dir()
    ]


_orchestrator_profile = _load_toml(PROJECT_ROOT / "agents" / "orchestrator.toml")
_instructions = _repo_relative(
    (PROJECT_ROOT / "prompts" / "orchestrator.md").read_text(encoding="utf-8")
)

agent = agents.Agent(
    name="orchestrator",
    description=_repo_relative(_orchestrator_profile["description"]),
    model=_resolve_model(_CONFIG["active_model"]),
    instructions=_instructions,
    subagents=_load_subagents(),
    subagent_policy=agents.SubagentPolicy(concurrent_child_turn_limit=32),
    environment=agents.MistralSandbox(),
    skills=_load_skills(),
    connectors=[agents.connector("web_search", run_as="deployment")],
    permission_mode="auto",
    permission_policy=_permission_policy(),
    **_model_settings(_CONFIG["active_model"]),
)
