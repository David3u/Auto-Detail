import click
import sys
from colorama import Fore, Style, init

@click.command()
def test():
    init(autoreset=True)

    pr_reasons = []

    print("╔══════════════════════════════════════╗")
    print("║  Enter a reason for this PR          ║")
    print("║  Use I:XX to reference issues        ║")
    print("║  (type '/quit' to finish)            ║")
    print("╚══════════════════════════════════════╝")

    reason = input(Fore.YELLOW + "➤ " + Style.RESET_ALL)
    while True:
        sys.stdout.write("\033[F\033[K")  
        if reason.strip() in ["", "/quit"]:
            break
        print(Fore.GREEN + "✔ Reason added:" + Style.RESET_ALL, reason)
        pr_reasons.append(reason)
        reason = input(Fore.YELLOW + "➤ " + Style.RESET_ALL)
    for _ in range(len(pr_reasons) + 5):
        sys.stdout.write("\033[F\033[K") 

    print(Fore.MAGENTA + "PR Reasons:")
    for r in pr_reasons:
        print("  - " + r)

