"""CLI of auto_detail."""

import click

from src import auto_detail


@click.group(invoke_without_command=True)
@click.version_option()
@click.pass_context
@click.option("--reasons", help="Reasons for the PR.", default="")
def main(ctx: click.Context, reasons: str):
    """A CLI tool to automatically generate pull request details."""
    if ctx.invoked_subcommand is None:
        auto_detail.main(reasons)


main.add_command(auto_detail.new)
main.add_command(auto_detail.list_details, name="list")
main.add_command(auto_detail.set_key)
main.add_command(auto_detail.set_base_branch, name="set-branch")
main.add_command(auto_detail.show_config, name="config")
