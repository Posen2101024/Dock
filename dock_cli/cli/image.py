import configparser
import itertools
import click
from dock_cli.utils import callback as cb
from dock_cli.utils import commands as cmd
from dock_cli.utils import helpers as hlp
from dock_cli.utils import utils
from dock_cli.utils.schema import ImageConfigOptions as Image, SectionType

@click.group(name='image', cls=hlp.OrderedGroup)
@click.pass_obj
def cli(obj):
    """Manage images

    This is a command line interface for manage images
    """
    obj.helper = hlp.ImageHelper(obj.config, obj.config_dir, obj.command)

@cli.command(name='list',
             help='List all images')
@click.pass_obj
def image_list(obj):
    for section in obj.helper.get_images():
        click.echo(section)

@cli.command(name='diff',
             help='List all images that have been changed between commits')
@click.pass_obj
@click.argument('commit1', required=False, type=str, default='HEAD')
@click.argument('commit2', required=False, type=str)
def image_diff(obj, commit1, commit2):
    for section in obj.helper.get_updated_images(commit1, commit2):
        click.echo(section)

@cli.command(name='show',
             help='Show detailed information about a specific image')
@click.pass_obj
@click.argument('section', required=True, type=str, callback=cb.validate_section)
@click.argument('tag', required=False, type=str, default='latest')
def image_show(obj, section, tag):
    click.echo(obj.helper.get_image(section, tag))

@cli.command(name='build',
             help='Build images')
@click.pass_obj
@click.argument('sections', nargs=-1, required=True, type=str, callback=cb.validate_section)
@click.option('--tag', 'tags', multiple=True, type=str, default=['latest'], show_default=True,
              help='Specify one or multiple tags for the image')
def image_build(obj, sections, tags):
    for section in sections:
        cmd.run([obj.command.docker, 'build', obj.helper.get_section_path(section),
                 '--file', obj.helper.get_section_file(section),
                 *itertools.chain(*[('--tag', obj.helper.get_image(section, tag)) for tag in tags])])

@cli.command(name='push',
             help='Push images')
@click.pass_obj
@click.argument('sections', nargs=-1, required=True, type=str, callback=cb.validate_section)
@click.option('--tag', 'tags', multiple=True, type=str, default=['latest'], show_default=True,
              help='Specify one or multiple tags for the image')
def image_push(obj, sections, tags):
    for section in sections:
        obj.helper.validate_section(section)
        for tag in tags:
            cmd.run([obj.command.docker, 'push', obj.helper.get_image(section, tag)])

@cli.command(name='clean',
             help='Clean images')
@click.pass_obj
@click.argument('sections', nargs=-1, required=True, type=str, callback=cb.validate_section)
@click.option('--tag', 'tags', multiple=True, type=str, default=['latest'], show_default=True,
              help='Specify one or multiple tags for the image')
def image_clean(obj, sections, tags):
    for section in sections:
        obj.helper.validate_section(section)
        for tag in tags:
            cmd.run([obj.command.docker, 'rmi', '--force', obj.helper.get_image(section, tag)])

@cli.group(name='config', invoke_without_command=True, cls=hlp.OrderedGroup)
@click.pass_context
def config_cli(ctx):
    """Manage images' configuration

    This is a command line interface for manage images' configuration
    """
    if ctx.invoked_subcommand is None:
        for section in ctx.obj.helper.get_images():
            utils.print_image_config(ctx.obj.config, section)

@config_cli.command(name='init',
                    help='Initialize image default settings in the configuration')
@click.pass_obj
@click.option('--registry', required=False, type=str, default='namespace',
              help='Default registry for all images.')
def config_init(obj, registry):
    utils.set_config_option(obj.config, configparser.DEFAULTSECT, Image.REGISTRY, registry)
    for section in obj.helper.get_images():
        utils.print_image_config(obj.config, section)
    utils.update_config(obj.config, obj.config_file)

@config_cli.command(name='add',
                    help='Add or update an image section in the configuration')
@click.pass_obj
@click.argument('section', required=True, type=click.Path(exists=True, file_okay=False),
                callback=cb.transform_to_section)
@click.option('--file', required=False, type=str, default='Dockerfile', show_default=True,
              help='Name of the Dockerfile for this section.')
@click.option('--name', required=False, type=str,
              help='Name of the image for this section.')
@click.option('--depends-on', required=False, multiple=True,
              type=click.Path(exists=True, file_okay=False),
              callback=cb.multiline_sections,
              help='List of sections or paths that this section depends on.')
def config_add(obj, section, file, name, depends_on):
    # pylint: disable=too-many-arguments
    if obj.config.has_section(section) is False:
        obj.config.add_section(section)
    utils.set_config_option(obj.config, section, Image.FILE, file)
    utils.set_config_option(obj.config, section, Image.NAME, name)
    utils.set_config_option(obj.config, section, Image.DEPENDS_ON, depends_on)
    utils.set_config_option(obj.config, section, Image.TYPE, SectionType.IMAGE)
    obj.helper.validate_section(section)
    utils.print_image_config(obj.config, section)
    utils.update_config(obj.config, obj.config_file)
