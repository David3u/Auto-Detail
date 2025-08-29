"""This module provides the CLI for auto_detail."""

import click
import auto_detail


@click.group(invoke_without_command=True)
@click.version_option()
@click.pass_context
@click.option("--reasons", help="Reasons for the PR.", default="")
def main(ctx: click.Context, reasons: str) -> None:
    """A CLI tool to automatically generate pull request details."""
    if ctx.invoked_subcommand is None:
        auto_detail.main(reasons)


main.add_command(auto_detail.new)
main.add_command(auto_detail.list)
