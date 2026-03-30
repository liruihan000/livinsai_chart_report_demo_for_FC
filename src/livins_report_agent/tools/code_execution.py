"""code_execution tool — runs Python in Anthropic sandbox, returns files."""

from __future__ import annotations

import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def create_code_execution_tool(api_key: str, model: str = "claude-haiku-4-5-20251001"):
    @tool
    def execute_code(code: str) -> str:
        """Execute Python code in a sandboxed environment to generate charts and PDF reports.

        The sandbox has matplotlib, reportlab, and other data science libraries pre-installed.
        Files MUST be saved to the path from os.getenv('OUTPUT_DIR', '.') to be retrievable.

        Example:
            import os, matplotlib.pyplot as plt
            output_dir = os.getenv('OUTPUT_DIR', '.')
            plt.figure(); plt.bar(['A','B'], [10,20])
            plt.savefig(os.path.join(output_dir, 'chart.png'), dpi=150)
            plt.close()

        Args:
            code: Python code to execute. Must save output files to OUTPUT_DIR.
        """
        import anthropic

        logger.info("execute_code ← code (%d chars):\n%.200s%s",
                     len(code), code, "..." if len(code) > 200 else "")

        client = anthropic.Anthropic(api_key=api_key)

        try:
            resp = client.beta.messages.create(
                model=model,
                max_tokens=16000,
                betas=["code-execution-2025-05-22"],
                tools=[{"type": "code_execution_20250522", "name": "code_execution"}],
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Execute the following Python code. "
                            "If it fails, fix the error and retry until it succeeds. "
                            "Do not change the intent — only fix bugs (imports, paths, syntax). "
                            "All output files MUST be saved to os.getenv('OUTPUT_DIR', '.').\n"
                            f"```python\n{code}\n```"
                        ),
                    }
                ],
            )
        except Exception as exc:
            logger.exception("Code execution API call failed")
            return json.dumps({"error": str(exc), "files": []})

        files = []
        stdout = ""
        stderr = ""
        return_code = -1

        for block in resp.content:
            if block.type == "code_execution_tool_result":
                r = block.content
                return_code = r.return_code
                stdout = r.stdout or ""
                stderr = r.stderr or ""
                for item in r.content:
                    if item.type == "code_execution_output" and hasattr(item, "file_id"):
                        # Try to get real filename from metadata
                        filename = getattr(item, "filename", None) or "output"
                        if filename == "output":
                            # Infer from stdout if possible
                            for ext in [".pdf", ".png", ".jpg", ".csv"]:
                                if ext in stdout.lower():
                                    import re
                                    match = re.search(r'[\w.-]+' + re.escape(ext), stdout)
                                    if match:
                                        filename = match.group(0)
                                        break
                        files.append({"file_id": item.file_id, "filename": filename})

        logger.info(
            "execute_code → rc=%d, files=%d, stdout=%d chars, stderr=%d chars",
            return_code, len(files), len(stdout), len(stderr),
        )
        if stderr:
            logger.warning("execute_code stderr:\n%.500s", stderr)
        if files:
            for f in files:
                logger.info("  file: %s (id=%s)", f["filename"], f["file_id"])

        return json.dumps({
            "return_code": return_code,
            "stdout": stdout,
            "stderr": stderr[:500] if stderr else "",
            "files": files,
        })

    return execute_code
