import os
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components


_COMPONENT_NAME = "rich_text_area"


def _get_build_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "frontend", "dist")


def _declare_component():
    # Dev server support via env var
    dev_url = os.environ.get("ST_RICH_TEXT_DEV")
    if dev_url:
        return components.declare_component(_COMPONENT_NAME, url="http://localhost:5173")

    build_dir = _get_build_dir()
    return components.declare_component(_COMPONENT_NAME, path=build_dir)


_component_func = _declare_component()


def st_rich_text_area(
    label: Optional[str] = None,
    value: str = "",
    *,
    height: int = 240,
    placeholder: str = "",
    toolbar: bool = True,
    key: Optional[str] = None,
):
    """Render a rich‑text, multi‑line editor that returns HTML.

    Parameters
    ----------
    label: Optional[str]
        An optional label that Streamlit renders above the component.
    value: str
        Initial HTML content for the editor.
    height: int
        Height of the editing area in pixels (not including toolbar).
    placeholder: str
        Placeholder shown when editor is empty.
    toolbar: bool
        Whether to show the formatting toolbar.
    key: Optional[str]
        Streamlit widget key.

    Returns
    -------
    str
        The editor contents as HTML (string). Returns the initial value until the user edits.
    """
    if label:
        st.markdown(f"**{label}**")

    result = _component_func(
        value=value,
        height=int(height),
        placeholder=placeholder,
        toolbar=bool(toolbar),
        key=key,
        default=value,
    )
    return result

