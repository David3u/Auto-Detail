"""Requirements:

GitPython
"""
import os
from git import Repo
import google.genai as genai
from google.genai import types
import uuid
from datetime import date
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString as LSS
from colorama import Fore, Style

DETAIL_ROOT = Path(".detail/notes")

def write_note(description: str, summary: str, type_: str) -> Path:
    """
    Write a note file in the same style as the notes reader expects.
    Returns the Path to the created file.
    """
    DETAIL_ROOT.mkdir(parents=True, exist_ok=True)

    # Unique filename like 2022-03-21-67c3d1.yaml
    today = date.today().strftime("%Y-%m-%d")
    suffix = uuid.uuid4().hex[:6]
    file_path = DETAIL_ROOT / f"{today}-{suffix}.yaml"

    # Use literal block scalars (|) and rely on ruamel.yaml's default chomping
    desc = LSS(description)
    summ = LSS(summary)
    typ  = LSS(type_)

    data = {
        "description": desc,
        "summary": summ,
        "type": typ,
    }

    yaml = YAML()
    yaml.indent(mapping=2, sequence=2, offset=2)
    yaml.width = 4096
    yaml.preserve_quotes = True

    with file_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)

    return file_path

def list_details():
    for file_path in DETAIL_ROOT.glob("*.yaml"):
        print(Fore.YELLOW + str(file_path) + Style.RESET_ALL)
        with file_path.open("r", encoding="utf-8") as f:
            print(f.read())
            
def clear_details():
    repo = Repo(".")
    repo_root = Path(repo.working_tree_dir).resolve()

    # Get untracked and unstaged files (relative to repo root)
    untracked = set(repo.untracked_files)
    unstaged = {item.a_path for item in repo.index.diff(None)}
    dirty_files = untracked | unstaged

    deleted = []
    for file_path in DETAIL_ROOT.glob("*.yaml"):
        abs_path = file_path.resolve()
        try:
            rel_path = str(abs_path.relative_to(repo_root))
        except ValueError:
            # file not inside repo, skip
            continue

        if rel_path in dirty_files:
            try:
                os.remove(abs_path)
                deleted.append(rel_path)
            except FileNotFoundError:
                pass

    return deleted

def get_diff():
    repo = Repo(".")
    return repo.git.diff()

def edit_detail(diff, detail, pr_reasons, edit):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    tools = [types.Tool(function_declarations=[new_detail_description])]
    config = types.GenerateContentConfig(
        system_instruction=f"You are a skilled software engineer. Your task is to effectively and skillfully review the diff of a pull request and edit a given detail.",
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode='ANY')
        ),
    )

    contents = [types.Content(role="user", parts=[types.Part(text=f"Oridinal detail: {detail}. Reasons for pr: {pr_reasons}. User edit request: {edit} Diff: {diff}")])]

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=config,
    )

    for fn in response.function_calls:
        if fn.name == "new_detail":
            summary = fn.args["summary"]
            pr_type = fn.args["type"]
            description = fn.args["description"]
            if pr_type == "trivial":
                description = ""
            return {"summary": summary, "type": pr_type, "description": description}
    
def generate_pr_details(diff, pr_reasons):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    tools = [types.Tool(function_declarations=[new_detail_description])]
    config = types.GenerateContentConfig(
        system_instruction=f"You are a skilled software engineer. Your task is to effectively and skillfully review the diff of a pull request and generate new PR detail(s). Reasons for pr: {pr_reasons}",
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode='ANY')
        ),
    )

    contents = [types.Content(role="user", parts=[types.Part(text=diff)])]

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=config,
    )

    details = []

    for fn in response.function_calls:
        if fn.name == "new_detail":
            summary = fn.args["summary"]
            pr_type = fn.args["type"]
            description = fn.args["description"]
            if pr_type == "trivial":
                description = ""
            details.append({"summary": summary, "type": pr_type, "description": description})

    return details

new_detail_description = {
    "name": "new_detail",
    "description": """This tool generates a new PR detail based on the diff of the last commit. Be minimal with the amount of details that you add. Details are used to quickly summarize what and why the PR was made.
    """,
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "summary": {
                "type": "STRING",
                "description": "A brief ~1 sentence summary of the PR.",
            },
            "type": {
                "type": "STRING",
                "description": "The type of PR",
                "enum": ["feature", "bug", "api", "trivial"],
            },
            "description": {
                "type": "STRING",
                "description": "A more detailed description of the PR. Should be under 60 words. You may leave as an empty string if the type is trivial.",
            },
        },
        "required": ["summary", "type", "description"],
    },
}
