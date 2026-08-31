"""
cli.py — Typer entrypoint for `sovai`.

`sovai`                   → launches the Textual TUI
`sovai doctor`            → checks all dependencies, prints fix commands
`sovai config edit`       → opens ~/.sovereignai/config.yaml in $EDITOR
`sovai models list`       → lists pulled Ollama models
`sovai models pull`       → pulls the four default models
`sovai kb add <path>`     → ingest a folder/file into the local knowledge base
`sovai kb status`         → show KB stats (doc count, chunk count, disk size)
`sovai kb watch <path>`   → watch a folder and re-ingest on changes
`sovai audit export`      → export a session audit to DOCX
`sovai run`               → alias for the default launch (TUI)
`sovai version`           → print version and exit
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from dotenv import load_dotenv

load_dotenv()
app = typer.Typer(
    name="sovai",
    help="SovereignAI — Local models. Local data. Zero external calls.",
    add_completion=False,
    no_args_is_help=False,
    invoke_without_command=True,
)

# Sub-command groups
models_app = typer.Typer(help="Manage Ollama models.")
kb_app     = typer.Typer(help="Manage the local knowledge base.")
config_app = typer.Typer(help="Manage configuration.")
audit_app  = typer.Typer(help="Manage audit logs.")

app.add_typer(models_app, name="models")
app.add_typer(kb_app,     name="kb")
app.add_typer(config_app, name="config")
app.add_typer(audit_app,  name="audit")


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Print version and exit."),
) -> None:
    """Launch the SovereignAI TUI (default action when no subcommand is given)."""
    if version:
        from sovereignai import __version__
        typer.echo(f"SovereignAI v{__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        _launch_tui()


def _launch_tui(workspace: str | None = None) -> None:
    """Import and run the Textual application."""
    from sovereignai.app import SovereignApp
    cwd = Path(workspace).resolve() if workspace else Path.cwd()
    app_instance = SovereignApp(workspace=cwd)
    app_instance.run()


# ── `sovai run` ────────────────────────────────────────────────────────────

@app.command("run")
def run_cmd(
    workspace: Optional[str] = typer.Option(
        None, "--workspace", "-w",
        help="Workspace directory (defaults to current directory).",
    ),
) -> None:
    """Launch the SovereignAI TUI."""
    _launch_tui(workspace)


# ── `sovai doctor` ────────────────────────────────────────────────────────

@app.command("doctor")
def doctor_cmd() -> None:
    """Check all dependencies and print fix commands for anything missing."""
    from sovereignai.config import doctor
    ok = doctor(verbose=True)
    raise typer.Exit(code=0 if ok else 1)


# ── `sovai version` ───────────────────────────────────────────────────────

@app.command("version")
def version_cmd() -> None:
    """Print version and exit."""
    from sovereignai import __version__
    from sovereignai.banner import get_banner_str
    typer.echo(get_banner_str())
    typer.echo(f"\nVersion: {__version__}")


# ── `sovai models` ────────────────────────────────────────────────────────

@models_app.command("list")
def models_list() -> None:
    """List all pulled Ollama models."""
    from sovereignai.config import get_config
    import ollama
    cfg = get_config()
    client = ollama.Client(host=cfg.ollama_host)
    try:
        result = client.list()
        typer.echo(f"\n{'Model':<40}  {'Size':>10}  {'Modified'}")
        typer.echo("─" * 65)
        for m in result.models:
            size_gb = (m.size or 0) / 1e9
            modified = str(m.modified_at)[:10] if m.modified_at else "unknown"
            typer.echo(f"  {m.model:<38}  {size_gb:>9.2f}G  {modified}")
        typer.echo()
    except Exception as e:
        typer.echo(f"❌  Cannot connect to Ollama at {cfg.ollama_host}: {e}", err=True)
        raise typer.Exit(1)


@models_app.command("pull")
def models_pull() -> None:
    """Pull all four default models required by SovereignAI."""
    from sovereignai.config import get_config
    import ollama
    cfg = get_config()
    client = ollama.Client(host=cfg.ollama_host)

    models_to_pull = [
        (cfg.router_model, "router — always-resident classifier"),
        (cfg.model_for("general"),  "general reasoning / drafting / summaries"),
        (cfg.model_for("coding"),   "coding / debugging / sandbox"),
        (cfg.model_for("vision"),   "vision / OCR / scanned docs"),
        (cfg.embedding_model,       "RAG embeddings"),
    ]

    typer.echo("\n📦  Pulling models (this may take a while — ~14GB total):\n")
    for tag, desc in models_to_pull:
        typer.echo(f"  ⬇  {tag}  ({desc})")
        try:
            for progress in client.pull(tag, stream=True):
                status = getattr(progress, "status", "")
                if "pulling" in status.lower() or "success" in status.lower():
                    typer.echo(f"     {status}", nl=False)
                    typer.echo("\r", nl=False)
            typer.echo(f"     ✅  {tag} ready                    ")
        except Exception as e:
            typer.echo(f"     ❌  Failed: {e}", err=True)

    typer.echo("\n✅  Done. Run `sovai doctor` to verify everything.\n")


# ── `sovai config` ────────────────────────────────────────────────────────

@config_app.command("edit")
def config_edit() -> None:
    """Open ~/.sovereignai/config.yaml in $EDITOR."""
    from sovereignai.config import open_config_in_editor
    open_config_in_editor()


@config_app.command("show")
def config_show() -> None:
    """Print the current merged configuration."""
    from sovereignai.config import get_config
    import yaml
    cfg = get_config()
    typer.echo(yaml.dump(cfg.raw(), default_flow_style=False))


# ── `sovai kb` ────────────────────────────────────────────────────────────

@kb_app.command("add")
def kb_add(
    path: str = typer.Argument(..., help="File or directory to ingest."),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="Recurse into subdirectories."),
) -> None:
    """Ingest a file or folder into the local knowledge base."""
    from sovereignai.knowledge_base.ingest import ingest_path
    p = Path(path).resolve()
    if not p.exists():
        typer.echo(f"❌  Path not found: {p}", err=True)
        raise typer.Exit(1)
    typer.echo(f"\n📚  Ingesting {p} …\n")
    stats = ingest_path(p, recursive=recursive, verbose=True)
    typer.echo(f"\n✅  Done — {stats['docs']} docs, {stats['chunks']} chunks ingested.\n")


@kb_app.command("status")
def kb_status() -> None:
    """Show knowledge base statistics."""
    from sovereignai.knowledge_base.store import get_store
    store = get_store()
    stats = store.stats()
    typer.echo(f"\n📚  Knowledge Base Status")
    typer.echo(f"   Documents : {stats['documents']}")
    typer.echo(f"   Chunks    : {stats['chunks']}")
    typer.echo(f"   Disk size : {stats['disk_mb']:.1f} MB")
    typer.echo(f"   Last ingest: {stats['last_ingest'] or 'never'}\n")


@kb_app.command("watch")
def kb_watch(
    path: str = typer.Argument(..., help="Directory to watch for changes."),
) -> None:
    """Watch a directory and re-ingest files when they change."""
    from sovereignai.knowledge_base.ingest import watch_path
    p = Path(path).resolve()
    if not p.is_dir():
        typer.echo(f"❌  Not a directory: {p}", err=True)
        raise typer.Exit(1)
    typer.echo(f"\n👁  Watching {p} for changes. Press Ctrl+C to stop.\n")
    watch_path(p)


# ── `sovai audit` ─────────────────────────────────────────────────────────

@audit_app.command("export")
def audit_export(
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID to export (latest if omitted)."),
    format: str = typer.Option("docx", "--format", "-f", help="Output format: docx | json | text"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path."),
) -> None:
    """Export an audit log to DOCX/JSON/text."""
    from sovereignai.orchestrator.audit_log import export_session
    out_path = export_session(session_id=session, fmt=format, output=output)
    typer.echo(f"\n✅  Audit exported to: {out_path}\n")


# ── Entrypoint ────────────────────────────────────────────────────────────

def main() -> None:
    app()


if __name__ == "__main__":
    main()

