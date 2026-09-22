# AutoMaticWorker

An open-source desktop workspace for configurable automation packages, authored by developers or AI and run through a common interface.

**v0.2.0 — M2 development build.** Import and upgrade local ZIP packages, configure generated forms, run or simulate tasks in managed processes, cancel execution, inspect logs and history, and download results.

[中文文档](README_ZH.md) · [Quick start (Chinese)](docs/QUICKSTART.md) · [Flow specification](docs/FLOW_SPEC.md) · [Authoring Skill](skills/automaticworker-flow-author/SKILL.md) · [Roadmap](ROADMAP.md)

## Run from source

Verified on Windows with Python 3.14.2, Node.js 24.12.0 and WebView2:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
npm ci --prefix vue_frontend
npm run build --prefix vue_frontend
.venv\Scripts\python.exe main.py
```

The desktop serves the built frontend on a dynamically selected loopback port. Use `--browser --port 5000` for browser mode, or `--data-dir output/workspace` for isolated development data. Closing the window cancels active work and stops the service.

The workspace offers two public examples: a synthetic data report and a temporary local web form. No business account is required. A standalone installer is planned for M4.

## Author packages

The repository includes manifest schema 1.0, `awm.sdk`, runnable templates and `python -m awm` commands: `init`, `validate`, `run`, `pack`. See the [authoring guide](docs/AUTHORING.md).

The [AI authoring Skill](skills/automaticworker-flow-author/SKILL.md) is a repository-dependent Alpha. Packages currently support the Python standard library and platform SDK only. Imported Python executes with local user privileges; capability declarations and separate processes are not an OS sandbox. Use trusted packages. Dry-run behavior is implemented by the author.

## Scope

The platform, specification, authoring Skill and synthetic examples are open source. Commercial services consist of custom workflow development, deployment adaptation and maintenance. Customer-specific workflows are delivered separately; see [public scope](docs/PUBLIC_SCOPE.md).

Vue 3 + TypeScript + Flask + Pywebview. MIT license retained.
