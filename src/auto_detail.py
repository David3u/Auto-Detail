"""This module provides the main CLI for auto_detail."""

import sys
import threading
from typing import List, Optional

import click
from colorama import Fore, Style, init
from InquirerPy import inquirer

from src import backend
from src import config


class BackgroundDetailGenerator:
    """Handles background generation of PR details."""

    def __init__(self):
        self.thread: Optional[threading.Thread] = None
        self.details: Optional[List[dict]] = None
        self.diff: Optional[str] = None
        self.error: Optional[Exception] = None
        self.completed: bool = False

    def start_generation(self, diff: str, pr_reasons: List[str]):
        """Start generating details in a background thread."""
        self.diff = diff
        self.thread = threading.Thread(
            target=self._generate_details,
            args=(diff, pr_reasons),
            daemon=True
        )
        self.thread.start()

    def _generate_details(self, diff: str, pr_reasons: List[str]):
        """Generate details in the background thread."""
        try:
            self.details = backend.generate_pr_details(diff, pr_reasons)
        except Exception as e:
            self.error = e
        finally:
            self.completed = True

    def get_details(self, timeout: Optional[float] = None) -> Optional[List[dict]]:
        """Get the generated details, waiting for completion if necessary."""
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)

        if self.error:
            raise self.error

        return self.details

    def is_ready(self) -> bool:
        """Check if details are ready without blocking."""
        return self.completed


class BackgroundDetailGenerator:
    """Handles background generation of PR details."""

    def __init__(self):
        self.thread: Optional[threading.Thread] = None
        self.details: Optional[List[dict]] = None
        self.diff: Optional[str] = None
        self.error: Optional[Exception] = None
        self.completed: bool = False

    def start_generation(self, diff: str, pr_reasons: List[str]):
        """Start generating details in a background thread."""
        self.diff = diff
        self.thread = threading.Thread(
            target=self._generate_details,
            args=(diff, pr_reasons),
            daemon=True
        )
        self.thread.start()

    def _generate_details(self, diff: str, pr_reasons: List[str]):
        """Generate details in the background thread."""
        try:
            self.details = backend.generate_pr_details(diff, pr_reasons)
        except Exception as e:
            self.error = e
        finally:
            self.completed = True

    def get_details(self, timeout: Optional[float] = None) -> Optional[List[dict]]:
        """Get the generated details, waiting for completion if necessary."""
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)

        if self.error:
            raise self.error

        return self.details

    def is_ready(self) -> bool:
        """Check if details are ready without blocking."""
        return self.completed


@click.command()
def set_key():
    """Store an API key in the config file."""
    key = click.prompt("Enter your Google Gemini API key", hide_input=True).strip()
    config.set_api_key(key)


@click.command()
@click.option("--reasons", help="Reasons for the PR.", default="")
def new(reasons: str):
    """Generates new pull request details."""
    main(reasons)


@click.command()
def list_details():
    """Lists all the detail files and their contents."""
    backend.list_details()


def _pretty_box():
    """Prints a pretty box with instructions for the user."""
    lines = [
        "Enter a reason for this PR",
        "Use #<issue_num> to reference the issue",
        "(Leave all blank to use pregenerated details)",
        "(Leave blank to finish)",
    ]

    width = max(len(line) for line in lines) + 4

    border_color = Fore.GREEN
    text_color = Fore.WHITE

    top = "╭" + "─" * width + "╮"
    bottom = "╰" + "─" * width + "╯"

    print(border_color + top)
    for line in lines:
        print(
            border_color
            + "│ "
            + text_color
            + line.center(width - 2)
            + border_color
            + " │"
        )
    print(border_color + bottom)


def _get_pr_reasons(initial_reasons: str) -> List[str]:
    """Gets the reasons for the PR from the user.

    Args:
        initial_reasons: The initial reasons for the PR.

    Returns:
        A list of reasons for the PR.
    """
    pr_reasons = [initial_reasons]

    _pretty_box()

    while True:
        reason = input(Fore.YELLOW + "➤ " + Style.RESET_ALL)
        sys.stdout.write("\033[F\033[K")
        if not reason.strip():
            break
        print(Fore.GREEN + "✔ Reason added:" + Style.RESET_ALL, reason)
        pr_reasons.append(reason.strip())

    return pr_reasons


def _confirm_clear_details():
    """Confirms with the user if they want to clear uncommitted details."""
    if inquirer.confirm(
        message="Clear currently uncommitted details?", default=True
    ).execute():
        print("Clearing details...")
        backend.clear_details()


def _review_details(details: List[dict], diff: str, pr_reasons: List[str]):
    """Handles the review process of the generated details.

    Args:
        details: A list of generated details.
        diff: The diff of the pull request.
        pr_reasons: The reasons for the pull request.
    """
    count = 1
    for detail in details:
        while True:
            print("=========================================")
            print(f"Reviewing detail {count} of {len(details)}")
            print(f"{Fore.YELLOW} - Summary: {Style.RESET_ALL}", detail["summary"])
            print(f"{Fore.YELLOW} - Type: {Style.RESET_ALL}", detail["type"])
            if detail["description"]:
                print(
                    f"{Fore.YELLOW} - Description: {Style.RESET_ALL}",
                    detail["description"],
                )
            print()

            action = inquirer.select(
                message="Approve or edit this detail.",
                choices=[
                    "Approve",
                    "Edit detail with AI",
                    "Edit detail manually",
                    "Restart",
                    "Quit",
                ],
                default=None,
            ).execute()

            if action == "Approve":
                file_path = backend.write_note(
                    detail["description"], detail["summary"], detail["type"]
                )
                print(
                    f"{Fore.GREEN}Detail approved and written to file: "
                    f"{file_path} {Style.RESET_ALL}"
                )
                break
            if action == "Edit detail with AI":
                edit = input("What should the AI change? ")
                detail = backend.edit_detail(diff, detail, pr_reasons, edit)
            elif action == "Edit detail manually":
                detail["summary"] = input("Enter a new summary: ")
                detail["type"] = inquirer.select(
                    message="Select a new type:",
                    choices=["feature", "bug", "api", "trivial"],
                    default=detail["type"],
                ).execute()
                if detail["type"] != "trivial":
                    detail["description"] = input("Enter a new description: ")
            elif action == "Restart":
                main()
                return
            elif action == "Quit":
                sys.exit(0)

        count += 1


def main(reasons: str = ""):
    """The main function for the auto_detail CLI."""
    init(autoreset=True)

    if not backend.test_repo():
        print(Fore.RED + "No git repository found at current location.")
        print(Style.RESET_ALL, end="")
        return

    diff = backend.get_diff()

    # start background generation with empty reasons
    bg_generator = BackgroundDetailGenerator()
    bg_generator.start_generation(diff, [""])

    pr_reasons = _get_pr_reasons(reasons)
    _confirm_clear_details()

    print("Generating PR details...")

    # use pregenerated if all reasons are empty/blank
    all_reasons_empty = all(not reason.strip() for reason in pr_reasons)

    if all_reasons_empty:
        if bg_generator.is_ready():
            details = bg_generator.get_details()
        else:
            details = bg_generator.get_details(timeout=30)  # 30 second timeout
    else:
        filtered_reasons = [reason.strip() for reason in pr_reasons if reason.strip()]
        details = backend.generate_pr_details(diff, filtered_reasons)

    if details:
        _review_details(details, diff, pr_reasons)
    else:
        print(Fore.RED + "Failed to generate PR details.")
        print(Style.RESET_ALL, end="")
