''' The ``config.tool`` module defines a simple command-line interface (CLI) program that can be
used as a development tool. It creates snippets that you can copy-paste into the Panorama
application project files like graph.json, or package.json of the business logic package.
'''
from typing import Mapping, Any
import sys
import argparse, json, textwrap
from .config import ConfigBase

def cli(name: str, config: ConfigBase) -> None:
    ''' Creates a simple command line interface for printing config snippets.

    Args:
        name (str): The name of your Panorama app
        config (ConfigBase): Instance of your configuration structure, subclass of ConfigBase.
    '''
    def render_template(template_path: str, variables: Mapping[str, Any]):
        try:
            from jinja2 import Environment, FileSystemLoader
        except ImportError:
            sys.exit('To use the render command you must install jinja2 with "pip install Jinja2"')
        env = Environment(loader=FileSystemLoader('/'), trim_blocks=True)
        env.filters['to_pretty_json'] = lambda value: json.dumps(value, indent=4)
        template = env.get_template(template_path)
        return template.render(variables)

    parser = argparse.ArgumentParser(description=textwrap.dedent(
        f'''\
        Configuration snippet generator for {name} application.

        This program can generate json and markdown snippets that you can copy-paste to the
        metadata and package definitions of your AWS Panorama project. The snippets contain the
        definitions of the application parameters in the required format. The following formats
        are supported:

         - nodes: generates a json snippet to be pasted in the nodeGraph.nodes field of graph.json
         - edges: generates a json snippet to be pasted in the nodeGraph.edges field of graph.json.
            Specify the code node name.
         - interface: generates json a snippet to be pasted in nodePackage.interfaces field of the
             package.json of the application code package
         - markdown: generates a markdown snippet that you can paste to the README of your project,
             or other parts of the documentation.
         - render: renders a Jinja2 template. Specify the template filename and the code node name.
         '''),
         formatter_class=argparse.RawDescriptionHelpFormatter
    )
    function_map = {
        'nodes' : lambda config, _: (
            print(json.dumps(config.get_panorama_definitions(), indent=4))
        ),
        'edges' : lambda config, kwargs: (
            print(json.dumps(config.get_panorama_edges(kwargs['code_node']), indent=4))
        ),
        'interface': lambda config, _: (
            print(json.dumps(config.get_panorama_app_interface(), indent=4))
        ),
        'markdown': (
            lambda config, _: print(config.get_panorama_markdown_doc())
        ),
        'render': lambda config, kwargs: (
            print(render_template(kwargs['template'], {
                'nodes': config.get_panorama_definitions(),
                'edges': config.get_panorama_edges(kwargs['code_node']),
                'interface': config.get_panorama_app_interface(),
                'markdown': config.get_panorama_markdown_doc()
            }))
        )
    }

    parser.add_argument('command', choices=function_map.keys(),
        help='Prints configuration snippets for graph.json nodes, edges, application '
             'interface in package.json, or in markdown format.'
    )
    parser.add_argument('--code-node', '-c', type=str, default='code_node',
        help='Code node name (used in edges snippet)'
    )
    parser.add_argument('--template', '-t', type=str,
        help='Template file (used in render command)'
    )

    args = parser.parse_args()
    func = function_map[args.command]
    func(config, {'code_node': args.code_node, 'template': args.template})

if __name__=='__main__':
    cli('config_base', ConfigBase())
