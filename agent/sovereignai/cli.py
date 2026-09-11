"""
cli.py — Typer entrypoint for `bastion`.

`bastion`                   → launches the Textual TUI
`bastion doctor`            → checks all dependencies, prints fix commands
`bastion config edit`       → opens ~/.bastion/config.yaml in $EDITOR
`bastion models list`       → lists configured models with display names
`bastion models pull`       → (no-op for Bastion — models are API-hosted)
`bastion kb add <path>`     → points to Supabase admin panel for ingestion
`bastion kb status`         → show Supabase KB stats (doc count, chunk count)
`bastion kb watch <path>`   → (not applicable — KB is managed via web admin panel)
`bastion audit export`      → export a session audit to DOCX
`bastion run`               → alias for the default launch (TUI)
`bastion version`           → print version and exit
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()
app = typer.Typer(
    name="bastion",
    help="Bastion — Sovereign AI agent. OpenAI-powered, Supabase-backed RAG.",
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
        typer.echo(f"Bastion v{__version__}")
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
    typer.echo(f"\nBastion v{__version__}")


# ── `sovai models` ────────────────────────────────────────────────────────

@models_app.command("list")
def models_list() -> None:
    """List configured models and their sovereign display names."""
    from sovereignai.config import get_config
    cfg = get_config()
    categories = ["general", "coding", "vision", "document_qa", "spreadsheet", "embedding"]
    typer.echo(f"\n{'Category':<15}  {'Display Name (TUI)':<22}  {'API Model'}")
    typer.echo("-" * 65)
    for cat in categories:
        node = cfg._raw.get("models", {}).get(cat, {})
        api_model = node.get("api") or node.get("model", "")
        display = node.get("display_name", api_model)
        typer.echo(f"  {cat:<13}  {display:<22}  {api_model}")
    typer.echo(f"\n  Provider: OpenAI API ({cfg.provider_base_url})\n")


@models_app.command("pull")
def models_pull() -> None:
    """Bastion uses the OpenAI API — no models to pull locally."""
    typer.echo(
        "\nℹ️  Bastion runs all models via the OpenAI API. No local download needed.\n"
        "    Make sure OPENAI_API_KEY is set in agent/.env and you're good to go.\n"
    )


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
    """Upload documents to the Bastion knowledge base (via web admin panel)."""
    typer.echo(
        f"\nℹ️  Bastion's knowledge base is hosted in Supabase and managed via the web admin panel.\n"
        f"    To ingest documents, go to the Bastion web app → Admin → Documents → Upload.\n"
        f"    The agent will automatically search all ingested documents when you ask questions.\n"
    )


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
    """KB watch mode is not available — use the web admin panel to manage documents."""
    typer.echo(
        "\nℹ️  Bastion's knowledge base is managed via the Supabase web admin panel.\n"
        "    KB watch mode is not supported in this version.\n"
    )


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

