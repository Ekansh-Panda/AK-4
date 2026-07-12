"""Browser automation tool via Playwright.

Lazy-imports playwright, gated behind COMPUTER_USE_BROWSER_ENABLED.
Uses a persistent browser context to preserve sessions/login state.
"""

from __future__ import annotations

import base64
from typing import Any, Literal

from app.core.config import settings
from app.core.logging import get_logger
from app.services.tools.base import Tool

logger = get_logger(__name__)

BrowserAction = Literal[
    "goto", "click", "type", "scroll", "screenshot", "pdf", "evaluate"
]


class BrowserTool(Tool):
    """Automate a Chromium browser via Playwright persistent context."""

    name = "browser"
    description = (
        "Control a Chromium browser: navigate pages, click elements, type text, "
        "scroll, take screenshots, export PDF, run JavaScript. "
        "Requires COMPUTER_USE_BROWSER_ENABLED and playwright installed."
    )
    requires_approval = True

    _browser = None
    _context = None
    _page = None

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["goto", "click", "type", "scroll", "screenshot", "pdf", "evaluate"],
                    "description": "Browser action to perform.",
                },
                "url": {
                    "type": "string",
                    "description": "URL to navigate to (for goto).",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for click/type/scroll targets.",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type (for type action).",
                },
                "script": {
                    "type": "string",
                    "description": "JavaScript to evaluate (for evaluate action).",
                },
                "x": {
                    "type": "integer",
                    "description": "X scroll offset or click coordinate.",
                },
                "y": {
                    "type": "integer",
                    "description": "Y scroll offset or click coordinate.",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename for screenshot/pdf.",
                },
            },
            "required": ["action"],
        }

    def run(self, **kwargs: Any) -> Any:
        if not settings.COMPUTER_USE_BROWSER_ENABLED:
            return {"error": "Browser is disabled (COMPUTER_USE_BROWSER_ENABLED=false)."}

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {"error": "playwright is not installed. Run: pip install playwright && playwright install chromium."}

        action: BrowserAction = kwargs.get("action", "goto")

        try:
            return self._execute(action, kwargs, sync_playwright)
        except Exception as exc:
            logger.error("Browser action failed: %s", exc)
            return {"error": str(exc), "action": action}

    def _execute(self, action: str, kwargs: dict[str, Any], sync_playwright: Any) -> Any:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Miori-Core/1.0",
            )
            page = context.new_page()

            try:
                if action == "goto":
                    url = kwargs.get("url", "about:blank")
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    return {"url": page.url, "title": page.title()}

                elif action == "click":
                    selector = kwargs.get("selector", "")
                    x = kwargs.get("x")
                    y = kwargs.get("y")
                    if selector:
                        page.click(selector, timeout=5000)
                        return {"status": "clicked", "selector": selector}
                    elif x is not None and y is not None:
                        page.mouse.click(x, y)
                        return {"status": "clicked", "x": x, "y": y}
                    return {"error": "selector or x/y required for click"}

                elif action == "type":
                    selector = kwargs.get("selector", "")
                    text = kwargs.get("text", "")
                    if not selector:
                        return {"error": "selector is required for type"}
                    page.fill(selector, text)
                    return {"status": "typed", "selector": selector, "length": len(text)}

                elif action == "scroll":
                    x = kwargs.get("x", 0)
                    y = kwargs.get("y", 500)
                    page.evaluate(f"window.scrollBy({x}, {y})")
                    return {"status": "scrolled", "x": x, "y": y}

                elif action == "screenshot":
                    filename = kwargs.get("filename", None)
                    screenshot_bytes = page.screenshot(full_page=False)
                    if filename:
                        Path(filename).write_bytes(screenshot_bytes)
                        return {"status": "saved", "path": filename, "size": len(screenshot_bytes)}
                    b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                    return {"status": "captured", "bytes": len(screenshot_bytes), "base64": b64}

                elif action == "pdf":
                    filename = kwargs.get("filename", "page.pdf")
                    pdf_bytes = page.pdf(format="A4")
                    Path(filename).write_bytes(pdf_bytes)
                    return {"status": "saved", "path": filename, "size": len(pdf_bytes)}

                elif action == "evaluate":
                    script = kwargs.get("script", "")
                    if not script:
                        return {"error": "script is required for evaluate"}
                    result = page.evaluate(script)
                    return {"result": result}

                else:
                    return {"error": f"Unknown browser action: {action}"}

            finally:
                context.close()
                browser.close()
