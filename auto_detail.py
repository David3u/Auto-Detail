import click
import sys
from colorama import Fore, Style, init
import backend
from InquirerPy import inquirer
from InquirerPy.base.control import Choice

@click.command()
@click.option("--reasons", help="Reasons for the PR.", default="")
def new(reasons):
    main(reasons)

@click.command()
def list():
    backend.list_details()


def pretty_box():
    lines = [
        "Enter a reason for this PR",
        "Use #issue_num to reference issues",
        "(Leave blank to finish)"
    ]

    width = max(len(line) for line in lines) + 4  # padding

    # Rounded borders
    top = "╭" + "─" * width + "╮"
    bottom = "╰" + "─" * width + "╯"

    border_color = Fore.GREEN    
    text_color = Fore.WHITE

    print(border_color + top)
    for line in lines:
        print(border_color + "│ " + text_color + line.center(width - 2) + border_color + " │")
    print(border_color + bottom)

def main(reasons):
    init(autoreset=True)

    pr_reasons = [reasons]

    pretty_box()

    reason = input(Fore.YELLOW + "➤ " + Style.RESET_ALL)
    while True:
        sys.stdout.write("\033[F\033[K")  
        if reason.strip() == "":
            break
        print(Fore.GREEN + "✔ Reason added:" + Style.RESET_ALL, reason)
        pr_reasons.append(reason.strip())
        reason = input(Fore.YELLOW + "➤ " + Style.RESET_ALL)

    clear = inquirer.confirm(message="Clear currently uncommited details?", default=True).execute()
    if clear:
        print("Clearing details...")
        backend.clear_details()


    print("Generating PR details...")

    diff = backend.get_diff()
    details = backend.generate_pr_details(diff, pr_reasons)

    count = 1
    for detail in details:
        while True:
            print("=========================================")
            print(f"Reviewing detail {count} of {len(details)}")
            print(f"{Fore.YELLOW} - Summary: {Style.RESET_ALL}", detail["summary"])
            print(f"{Fore.YELLOW} - Type: {Style.RESET_ALL}", detail["type"])
            if detail["description"] != "":
                print(f"{Fore.YELLOW} - Description: {Style.RESET_ALL}", detail["description"])
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
            print()
            if action == "Approve":
                file_path = backend.write_note(detail["description"], detail["summary"], detail["type"])
                print(f"{Fore.GREEN}Detail approved and written to file: {file_path} {Style.RESET_ALL}")
                break
            elif action == "Edit detail with ai":
                edit = input("What should the llm change? ")
                detail = backend.edit_detail(diff, detail, pr_reasons, edit)
            elif action == "Edit detail manually":
                detail["summary"] = input("Enter a new summary: ")
                detail["type"] = inquirer.select(
                message="Select a new type:",
                    choices=[
                        "feature",
                        "bug",
                        "api",
                        "trivial",
                    ],
                    default=detail["type"],
                ).execute()
                detail["description"] = input("Enter a new description: ")
            elif action == "Restart":
                main()
                return
            elif action == "Quit":
                sys.exit(0)
        count += 1