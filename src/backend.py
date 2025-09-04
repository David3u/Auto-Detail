"""This module provides backend functionality for auto_detail."""

import os
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from colorama import Fore, Style
from git import Repo
from google import genai
from google.genai import types
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString as LSS
from src import config

DETAIL_ROOT = Path(".detail/notes")


def write_note(description: str, summary: str, type_: str) -> Path:
    """Write a note file in the same style as the notes reader expects.

    Args:
        description: The detailed description of the pull request.
        summary: A brief summary of the pull request.
        type_: The type of the pull request (e.g., "feature", "bug").

    Returns:
        The path to the created note file.
    """
    DETAIL_ROOT.mkdir(parents=True, exist_ok=True)

    today = date.today().strftime("%Y-%m-%d")
    suffix = uuid.uuid4().hex[:6]
    file_path = DETAIL_ROOT / f"{today}-{suffix}.yaml"

    data = {
        "summary": LSS(summary),
        "type": LSS(type_),
        "description": LSS(description),
    }

    if description == "":
        del data["description"]

    yaml = YAML()
    yaml.indent(mapping=2, sequence=2, offset=2)
    yaml.width = 4096
    yaml.preserve_quotes = True

    with file_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)

    return file_path


def list_details():
    """Prints all the detail files and their contents."""
    for file_path in DETAIL_ROOT.glob("*.yaml"):
        print(Fore.YELLOW + str(file_path) + Style.RESET_ALL)
        with file_path.open("r", encoding="utf-8") as f:
            print(f.read())


def clear_details() -> List[str]:
    """Removes all untracked and unstaged detail files.

    Returns:
        A list of the deleted file paths.
    """
    repo = Repo(".")
    repo_root = Path(repo.working_tree_dir).resolve()

    untracked = set(repo.untracked_files)
    unstaged = {item.a_path for item in repo.index.diff(None)}
    dirty_files = untracked | unstaged

    deleted = []
    for file_path in DETAIL_ROOT.glob("*.yaml"):
        abs_path = file_path.resolve()
        try:
            rel_path = str(abs_path.relative_to(repo_root))
        except ValueError:
            continue

        if rel_path in dirty_files:
            try:
                os.remove(abs_path)
                deleted.append(rel_path)
            except FileNotFoundError:
                pass

    return deleted


def get_diff() -> str:
    """Gets the diff of the current repository against the configured base branch.

    Returns:
        The diff of the current repository against the base branch.
    """
    repo = Repo(".")
    base_branch = config.get_base_branch()

    try:
        # Try to get diff against the configured base branch
        diff_output = repo.git.diff(base_branch)
        if diff_output.strip():
            return diff_output
        # If no diff against base branch, fall back to working directory changes
        return _get_working_directory_diff(repo)
    except Exception:
        # If base branch doesn't exist or other error, fall back to working directory changes
        return _get_working_directory_diff(repo)


def _get_working_directory_diff(repo) -> str:
    """Gets the diff of working directory changes (original behavior).

    Args:
        repo: The git repository object.

    Returns:
        The diff of the working directory changes.
    """
    diffs = []

    # Unstaged changes
    diffs.append(repo.git.diff())

    # Staged changes
    diffs.append(repo.git.diff("--cached"))

    # Deleted files (unstaged or staged)
    deleted_unstaged = repo.git.diff("--diff-filter=D")
    deleted_staged = repo.git.diff("--cached", "--diff-filter=D")
    diffs.extend([deleted_unstaged, deleted_staged])

    # New (untracked) files
    for f in repo.untracked_files:
        if not os.path.isfile(f):
            continue  # skip dirs, broken symlinks, etc.
        try:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            diffs.append(
                f"diff --git a/{f} b/{f}\n"
                f"new file mode 100644\n"
                f"--- /dev/null\n"
                f"+++ b/{f}\n" + "\n".join(f"+{line}" for line in content.splitlines())
            )
        except FileNotFoundError as e:
            diffs.append(
                f"diff --git a/{f} b/{f}\n"
                f"new file mode 100644\n"
                f"--- /dev/null\n"
                f"+++ b/{f}\n"
                f"+[Could not read file: {e}]"
            )
        except Exception as e:
            diffs.append(
                f"diff --git a/{f} b/{f}\n"
                f"new file mode 100644\n"
                f"--- /dev/null\n"
                f"+++ b/{f}\n"
                f"+[Could not read file: {e}]"
            )

    return "\n".join(d.strip() for d in diffs if d.strip())


def _get_gemini_client() -> genai.Client:
    """Initializes and returns the Gemini API client.

    Returns:
        The Gemini API client.
    """
    return genai.Client(api_key=config.get_api_key())


def _get_new_detail_description() -> Dict[str, Any]:
    """Returns the tool description for the new_detail function."""
    return {
        "name": "new_detail",
        "description": "Generate a new pull request detail from the last commit diff.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "summary": {
                    "type": "STRING",
                    "description": (
                        "One short sentence (<20 words) summarizing the PR. "
                        "Be concise, clear, and avoid filler words."
                    ),
                },
                "type": {
                    "type": "STRING",
                    "description": "The PR category. API is a MAJOR change to the public API.",
                    "enum": ["feature", "bug", "api", "trivial"],
                },
                "description": {
                    "type": "STRING",
                    "description": (
                        "A clear, concise explanation of the PR (under 60 words)."
                    ),
                },
            },
            "required": ["summary", "type", "description"],
        },
    }


def _generate_content(
    client: genai.Client, system_instruction: str, content: List[types.Content]
) -> genai.types.GenerateContentResponse:
    """Generates content using the Gemini API.

    Args:
        client: The Gemini API client.
        system_instruction: The system instruction for the model.
        content: The content to be sent to the model.

    Returns:
        The response from the Gemini API.
    """
    tools = [types.Tool(function_declarations=[_get_new_detail_description()])]
    model_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY")
        ),
    )

    return client.models.generate_content(
        model="gemini-2.5-flash",
        contents=content,
        config=model_config,
    )


def edit_detail(diff: str, detail: str, pr_reasons: str, edit: str) -> Dict[str, str]:
    """Edits a pull request detail using the Gemini API.

    Args:
        diff: The diff of the pull request.
        detail: The original detail of the pull request.
        pr_reasons: The reasons for the pull request.
        edit: The user's edit request.

    Returns:
        A dictionary containing the edited summary, type, and description.
    """
    client = _get_gemini_client()
    system_instruction = (
        "You are a skilled software engineer. Your task is to effectively and skillfully "
        "review the diff of a pull request and edit a given detail."
    )
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=f"Oridinal detail: {detail}. Reasons for pr: {pr_reasons}. "
                    f"User edit request: {edit} Diff: {diff}"
                )
            ],
        )
    ]

    response = _generate_content(client, system_instruction, contents)

    for fn in response.function_calls:
        if fn.name == "new_detail":
            summary = fn.args["summary"]
            pr_type = fn.args["type"]
            description = fn.args["description"]
            if pr_type == "trivial":
                description = ""
            return {"summary": summary, "type": pr_type, "description": description}
    return {}


def generate_pr_details(diff: str, pr_reasons: str) -> List[Dict[str, str]]:
    """Generates pull request details using the Gemini API.

    Args:
        diff: The diff of the pull request.
        pr_reasons: The reasons for the pull request.

    Returns:
        A list of dictionaries, each containing the summary, type, and description of a detail.
    """
    client = _get_gemini_client()
    system_instruction = (
        "You are a senior software engineer. Review the pull request diff and "
        "write a clear and concise description of the changes. "
        "Generate a new PR detail in simple language. "
        "You may generate multiple details if necessary. "
        f"\n\n Reasons for pr: {pr_reasons}"
    )
    contents = [types.Content(role="user", parts=[types.Part(text=diff)])]

    response = _generate_content(client, system_instruction, contents)

    details = []
    for fn in response.function_calls:
        if fn.name == "new_detail":
            summary = fn.args["summary"]
            pr_type = fn.args["type"]
            description = fn.args["description"]
            if pr_type == "trivial":
                description = ""
            details.append(
                {"summary": summary, "type": pr_type, "description": description}
            )

    return details


def test_repo() -> bool:
    """Tests the current folder to see if there is a git repo.

    Returns:
        True if there exists a git repo and false if not.
    """

    try:
        Repo(".")
        return True
    except:
        return False
