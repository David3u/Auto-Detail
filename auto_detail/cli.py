"""CLI of auto_detail."""

import click

from auto_detail import auto_detail_main


@click.group(invoke_without_command=True)
@click.version_option()
@click.pass_context
@click.option("--reasons", help="Reasons for the PR.", default="")
def main(ctx: click.Context, reasons: str):
    """A CLI tool to automatically generate pull request details."""
    if ctx.invoked_subcommand is None:
        auto_detail_main.main(reasons)


main.add_command(auto_detail_main.new)
main.add_command(auto_detail_main.list_details, name="list")
main.add_command(auto_detail_main.set_key)
main.add_command(auto_detail_main.set_base_branch, name="set-branch")
main.add_command(auto_detail_main.show_config, name="config")
