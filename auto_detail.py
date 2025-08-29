"""This module provides the main CLI for auto_detail."""

import sys
from typing import List

import click
from colorama import Fore, Style, init
from InquirerPy import inquirer

import backend


@click.command()
@click.option("--reasons", help="Reasons for the PR.", default="")
def new(reasons: str) -> None:
    """Generates new pull request details."""
    main(reasons)


@click.command()
def list() -> None:
    """Lists all the detail files and their contents."""
    backend.list_details()


def _pretty_box() -> None:
    """Prints a pretty box with instructions for the user."""
    lines = [
        "Enter a reason for this PR",
        "Use #issue_num to reference issues",
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


def _confirm_clear_details() -> None:
    """Confirms with the user if they want to clear uncommitted details."""
    if inquirer.confirm(
        message="Clear currently uncommited details?", default=True
    ).execute():
        print("Clearing details...")
        backend.clear_details()


def _review_details(details: List[dict], diff: str, pr_reasons: List[str]) -> None:
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
                    "Edit detail with ai",
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
            if action == "Edit detail with ai":
                edit = input("What should the llm change? ")
                detail = backend.edit_detail(diff, detail, pr_reasons, edit)
            elif action == "Edit detail manually":
                detail["summary"] = input("Enter a new summary: ")
                detail["type"] = inquirer.select(
                    message="Select a new type:",
                    choices=["feature", "bug", "api", "trivial"],
                    default=detail["type"],
                ).execute()
                detail["description"] = input("Enter a new description: ")
            elif action == "Restart":
                main()
                return
            elif action == "Quit":
                sys.exit(0)

        count += 1


def main(reasons: str = "") -> None:
    """The main function for the auto_detail CLI."""
    init(autoreset=True)

    pr_reasons = _get_pr_reasons(reasons)
    _confirm_clear_details()

    print("Generating PR details...")

    diff = backend.get_diff()
    details = backend.generate_pr_details(diff, pr_reasons)

    _review_details(details, diff, pr_reasons)
