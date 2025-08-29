import click
import sys
from colorama import Fore, Style, init
import backend
from InquirerPy import inquirer
from InquirerPy.base.control import Choice

@click.command()
def new():
    main()

def main():
    init(autoreset=True)

    pr_reasons = []

    print("╔══════════════════════════════════════╗")
    print("║  Enter a reason for this PR          ║")
    print("║  Use I:XX to reference issues        ║")
    print("║  (leave blank to finish)             ║")
    print("╚══════════════════════════════════════╝")

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