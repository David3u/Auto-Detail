import click
import InquirerPy 
import auto_detail

@click.group()
@click.version_option()
@click.pass_context
def main(ctx: click.Context):
    pass

main.add_command(auto_detail.test)
