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

        logger.info("execute_code ← code (%d chars):\n%s", len(code), code)

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

        raw_file_ids: list[str] = []
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
                        raw_file_ids.append(item.file_id)

        # Extract filenames from stdout (savefig/doc.build print output)
        import re
        known_files = re.findall(r'[\w./-]+\.(?:png|pdf|jpg|csv|svg)', stdout, re.IGNORECASE)
        # Deduplicate while preserving order
        seen = set()
        unique_files = []
        for f in known_files:
            basename = f.rsplit("/", 1)[-1]  # strip path
            if basename not in seen:
                seen.add(basename)
                unique_files.append(basename)

        # Match file_ids to filenames by order; extras get output_N names
        files = []
        for i, fid in enumerate(raw_file_ids):
            if i < len(unique_files):
                filename = unique_files[i]
            else:
                filename = f"output_{i + 1}"
            files.append({"file_id": fid, "filename": filename})

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
