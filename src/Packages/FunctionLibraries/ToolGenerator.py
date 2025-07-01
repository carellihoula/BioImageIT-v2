from pathlib import Path
import inspect
import textwrap


class Tool:
    name = "PLACEHOLDER_TOOL_NAME"
    description = "Tool description."
    categories = ['Workflow']
    environment = 'environmentName'
    dependencies = dict(python='==3.10', conda=[], pip=[])
    inputs = [
            dict(
                names=['-i', '--input_image'],
                help='The input image path.',
                required=True,
                type='Path',
                autoColumn=True,
            ),
        ]
    outputs = [
            dict(
                names=['-o', '--output_image'],
                help='The output image.',
                default='{input_image.stem}_detections{input_image.exts}',
                type='Path',
            ),
        ]

    def initialize(self, args):
            print('Loading libraries...')

    def processDataFrame(self, dataFrame, argsList):
            return dataFrame

    def processData(self, args):
            return


def write_tool_file(path: Path, tool_name: str = "Tool"):
    class_source = inspect.getsource(Tool)
    class_source = class_source.replace('"PLACEHOLDER_TOOL_NAME"', f'"{tool_name}"')
    # Adds missing imports
    header = "from pathlib import Path\nimport argparse\n\n"
    content = header + textwrap.dedent(class_source)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
