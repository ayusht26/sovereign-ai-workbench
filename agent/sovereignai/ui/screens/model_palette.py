"""
model_palette.py — /models command palette.

Fixed: build ListView by passing items to constructor (not lv.append in compose).
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import ListView, ListItem, Label, Static
from textual.containers import Vertical


class ModelListItem(ListItem):
    """List item storing a model tag or command value."""
    def __init__(self, label: str, value: str, **kwargs) -> None:
        super().__init__(Label(label), **kwargs)
        self.value = value


class ModelPalette(ModalScreen):
    """Modal model selector. Dismiss with selected model string or None."""

    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
    ]

    DEFAULT_CSS = """
    ModelPalette {
        align: center middle;
        background: rgba(0,0,0,0.7);
    }
    ModelPalette > Vertical {
        width: 68;
        height: auto;
        max-height: 24;
        background: #1a1d22;
        border: solid #5FA8D3;
        padding: 1 2;
    }
    ModelPalette #title {
        color: #5FA8D3;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
        padding: 0 1;
    }
    ModelPalette ListView {
        background: transparent;
        border: none;
        height: auto;
        padding: 0;
    }
    ModelPalette ListItem {
        color: #cdd6f4;
        padding: 0 1;
        height: 1;
        background: transparent;
    }
    ModelPalette ListItem.--highlight {
        background: #2e3a4a;
        color: #5FA8D3;
    }
    ModelPalette .hint {
        color: #445566;
        text-style: italic;
        height: 1;
        margin-top: 1;
        padding: 0 1;
    }
    ModelPalette .sep {
        color: #2e3440;
        height: 1;
        padding: 0 1;
    }
    """

    def __init__(self, current_model: str = "AUTO", **kwargs) -> None:
        super().__init__(**kwargs)
        self._current = current_model

    def compose(self) -> ComposeResult:
        from sovereignai.config import get_config
        cfg = get_config()

        rows = [
            ("AUTO",                    "Auto-detect the right model per task",   True),
            (cfg.model_for("general"),  "General reasoning, drafting, summaries", False),
            (cfg.model_for("coding"),   "Coding, debugging, running code",         False),
            (cfg.model_for("vision"),   "Images, scanned docs, drawings, OCR",     False),
        ]

        # Build all ListItems with clean ModelListItem objects (no invalid DOM ids)
        list_items: list[ListItem] = []
        for model_tag, desc, is_auto in rows:
            is_selected = (model_tag == self._current) or (self._current == "AUTO" and is_auto)
            marker = "●" if is_selected else " "
            display = "AUTO" if is_auto else model_tag
            label_text = f"{marker} {display:<24} {desc}"
            list_items.append(ModelListItem(label_text, value=model_tag))

        # Separator + commands
        list_items.append(ListItem(Label("─" * 58), disabled=True))
        list_items.append(ModelListItem("  /kb    Manage local knowledge base", value="/kb"))
        list_items.append(ModelListItem("  /net   Open network monitor",         value="/net"))

        with Vertical():
            yield Static("  Model Selection", id="title")
            yield ListView(*list_items, id="model-list")
            yield Static("  ↑↓ navigate   enter select   esc cancel", classes="hint")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, ModelListItem) and item.value:
            self.dismiss(item.value)
        else:
            self.dismiss(None)
