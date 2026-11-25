# My-vibe-work
Repozytorium do pracy dla Mistral Vibe Code Web

## Agent-orchestrator (Mistral Agents SDK)

Konwersacyjny agent-orchestrator zbudowany przy użyciu Mistral Agents SDK. Zawartość repozytorium
https://github.com/pavelpenev/.vibe jest sklonowana w całości do katalogu głównego, dokładnie w
oryginalnej formie:

- `prompts/orchestrator.md` — system prompt orchestratora,
- `agents/*.toml` (+ `agents/doc-reviewer.references/`) — profile 11 subagentów z pełnymi instrukcjami,
- `skills/` — 9 skilli,
- `scripts/` — skrypt `extract_lisp_forms.py`,
- `config.toml` — konfiguracja modeli.

Jedyne kodu napisany od zera to pętla agenta w `main.py`:

- główny agent `orchestrator`: `instructions` z `prompts/orchestrator.md`,
- po jednym `agents.Subagent` dla każdego profilu z `agents/*.toml` (oryginalne `description`,
  `instructions`, model z `active_model` przez aliasy z `config.toml`, `thinking`/`temperature`
  → `reasoning_effort`/`temperature`); model niedostępny na koncie zastępowany `mistral-large-4`
  (`AVAILABLE_MODELS`/`FALLBACK_MODEL` w `main.py` — wszystkie modele z `config.toml` są dostępne),
- skille jako `LocalSkillBundle` z katalogu `skills/`,
- polityka uprawnień: `PermissionPolicy` z denylistą komend bash z `[tools.bash].denylist`
  plików agentów (reguła `file_system.bash`, reszta `allow`, `permission_mode="auto"`),
- ścieżki `~/.vibe/...` w instrukcjach zamieniane na względne wobec repozytorium (`./prompts/...`,
  `./workspaces/...`),
- konektor `tavily` (sklep Studio, klucz Tavily jako **workspace credential**,
  `run_as="deployment"` — bez OBO/hardeningu, działa unattended) daje agentom narzędzia
  wyszukiwania/fetchowania stron (odpowiednik `web_search`/`web_fetch`); subagenci, których
  `enabled_tools` w profilu nie zawiera web, dostają `connectors=[]` (czysty zbiór),
- `environment=MistralSandbox()` (rola `cloud_user`), `subagent_policy` limit 32 współbieżnych
  subagentów, `builtins=Builtins(subagents=False)` na subagentach (drzewo 2 poziomy).

## Uruchomienie lokalne

```bash
uv sync
printf 'MISTRAL_API_KEY=<klucz>\n' > .env
uv run --env-file .env agents chat
```

## Wdrożenie zarządzane (Mistral Cloud) — `agents deploy`

```bash
git push origin main
uv run --env-file .env agents deploy        # buduje wypchnięty commit, rejestruje agenta "orchestrator"
```

Wdrożenie: deployment `orchestrator`, agent `orchestrator` (Managed Agents w Studio).

## Współpraca z agentem przez Vibe

- **Vibe Code Web**: adres zwrócony przez deploy,
  `https://chat.mistral.ai/managed-agents/orchestrator?source=agents_api&shareContext=...`
  — rozmowy z agentem; projekt z GitHub ląduje w sandboxie sesji (cwd).
- **Studio**: `console.mistral.ai/build/managed-agents` — agent, sesje (`/sessions`), trace.
- **CLI / programowo**: `uv run agents chat orchestrator` albo
  `agents.Agent.load_from(agent_name="orchestrator")`.

## Uwagi

- web idzie przez konektor **Tavily**: dodaj go w Studio
  (`console.mistral.ai/connectors/marketplace?template=tavily`) z kluczem Tavily jako
  workspace credential, potem `agents deploy` — agent używa go jako `run_as="deployment"`.
- Narzędzia `agents.spawn`/`agents.list` z oryginalnego promptu zastępuje w SDK wbudowany zestaw
  narzędzi subagentów; limity per-typ zostają polityką w instrukcjach.
