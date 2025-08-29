import click
import InquirerPy 
import auto_detail

@click.group(invoke_without_command=True)
@click.version_option()
@click.pass_context
def main(ctx: click.Context):
    auto_detail.main()

main.add_command(auto_detail.new)
