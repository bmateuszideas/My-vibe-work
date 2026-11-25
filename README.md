# My-vibe-work
Repozytorium do pracy dla Mistral Vibe Code Web

## Agent-orchestrator (Mistral Agents SDK)

Konwersacyjny agent-orchestrator zbudowany przy użyciu Mistral Agents SDK, skonfigurowany
jeden do jednego z repozytorium https://github.com/pavelpenev/.vibe (zvendowany w `vibe/`).

- `vibe/` — konfiguracja 1:1 z `pavelpenev/.vibe`: `agents/*.toml` (profile subagentów),
  `prompts/orchestrator.md` (system prompt), `skills/` (skille), `config.toml` (modele),
  `scripts/`.
- `main.py` — buduje `agents.Agent` o nazwie `orchestrator`:
  - instrukcje wczytywane verbatim z `vibe/prompts/orchestrator.md`;
  - 11 subagentów generowanych z `vibe/agents/*.toml` (name = nazwa pliku, description,
    instructions, model z `active_model` mapowanego przez aliasy z `config.toml`,
    `thinking`/`temperature` modelu → `reasoning_effort`/`temperature`);
  - skille z `vibe/skills/` jako `LocalSkillBundle`;
  - środowisko `MistralSandbox` (wymaga roli `cloud_user` u service account wdrożenia);
  - `subagent_policy` z `concurrent_child_turn_limit=32` (odpowiednik limitu 32 aktywnych
    subagentów z oryginalnego promptu; drzewo 2 poziomy jak w SDK);
  - `permission_mode="auto"` (odpowiednik `default_approval_policy = "auto-approve"`).
- `Dockerfile` — obraz workera dla wdrożenia zarządzanego (`CMD ["agents", "run-worker"]`).

## Uruchomienie lokalne

```bash
uv sync
printf 'MISTRAL_API_KEY=<klucz>\n' > .env
uv run --env-file .env agents chat
```

## Wdrożenie zarządzane na Mistral Cloud (Studio)

Kod musi być zpushowany do GitHub — wdrożenie buduje obraz z commita:

```bash
git push origin <branch>
# przez Mistral MCP: deploy_workflow_deployment(deployment_name="vibe-orchestrator",
#   github_url="https://github.com/bmateuszideas/My-vibe-work", revision="<commit SHA>",
#   build_directory=".", dockerfile_path="Dockerfile",
#   service_account_roles=["cloud_user"])   # rola wymagana przez MistralSandbox
# lub lokalnie: uv run agents deploy
```

## Współpraca z agentem przez Vibe

- **Vibe Code Web**: po deployu agent jest dostępny pod adresem zwróconym przez deploy,
  `https://chat.mistral.ai/managed-agents/orchestrator?source=agents_api` — tam prowadzisz
  konwersacje (sesje), a w razie potrzeby Vibe Code Web klonuje też repozytorium GitHub
  do sandboxa sesji.
- **Mistral Studio**: `console.mistral.ai/build/managed-agents` — lista agentów, sesje
  (`/sessions`) i trace (OpenTelemetry) każdego turna.
- **CLI / programowo**: `uv run agents chat orchestrator` albo
  `agents.Agent.load_from(agent_name="orchestrator")` w dowolnej aplikacji Python.

## Różnice względem oryginalnej konfiguracji Vibe CLI

- Narzędzia `agents.spawn` / `agents.list` / `agents.send_message` z promptu zastępuje
  w SDK wbudowany zestaw narzędzi subagentów: subagenty deklaruje się po nazwie
  (lista w system prompt), model uruchamia je, przesyła wiadomości i czeka na wyniki;
  limity per-typ (1× designer/planner/plan-reviewer/design-reviewer, 4× pozostałe)
  pozostają polityką w instrukcjach, a limit współbieżności egzekwuje `subagent_policy`.
- `web_search` / `web_fetch` nie są wbudowanymi narzędziami Agents SDK — w tej konfiguracji
  nie są podłączone (wymagałyby konektora lub zdalnego MCP); subagenci używają plików,
  basha i skillów z sandboxa.
- Ścieżki `~/.vibe/...` z oryginalnego promptu w sandboxie sesji odpowiadają katalogowi
  roboczemu sesji (repozytorium GitHub wybrane w Vibe Code Web).
