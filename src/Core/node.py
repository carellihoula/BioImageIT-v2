import json
import re
from pathlib import Path
from importlib import import_module
from typing import Any, cast
from src.Core.utils import DictToObject, get_root_path
from wetlands.environment import Environment
from wetlands.external_environment import ExternalEnvironment
from wetlands.environment_manager import EnvironmentManager
import pandas
from send2trash import send2trash

PARAMETERS_PATH = 'parameters.json'
OUTPUT_DATAFRAME_PATH = 'output_data_frame.csv'

class Node:
    parameters: dict
    environment: Environment

    def __init__(self, environment_manager: EnvironmentManager, toolPath: Path, tool, moduleImportPath:str, workflowPath: Path, workflowTool: bool) -> None:
        self._environment_manager = environment_manager
        self.name = toolPath.stem
        self.path = toolPath
        self.importPath = moduleImportPath
        self.tool = tool
        self.workflowPath = workflowPath.resolve()
        self.workflowTool = workflowTool
        self.initializeParameters()

# Parameters
    def initializeInput(self, input):
        defaultValue = input.get('default')
        defaultValue = input['choices'][0] if defaultValue is None and 'choices' in input and len(input['choices']) > 0 else defaultValue
        return dict(type='columnName' if input.get('autoColumn', False) else 'value', columnName=None, value=defaultValue, defaultValue=defaultValue, dataType=input['type'], advanced=input.get('advanced'))

    def initializeOutput(self, output):
        return dict(value=output.get('default'), 
                    defaultValue=output.get('default'), 
                    dataType=output['type'], 
                    extension=output.get('extension'),
                    editable=output.get('editable'),
                    help=output.get('help'))

    def initializeParameters(self):
        inputs = { input['name']: self.initializeInput(input) for input in self.tool.inputs }
        outputs = { output['name']: self.initializeOutput(output) for output in self.tool.outputs }
        self.parameters = dict(inputs=inputs, outputs=outputs)



# Manage arguments

    def setArg(self, args, parameterName, parameter, parameterValue, index):
        arg = parameterValue
        if parameter['dataType'] == 'Path' and arg is not None:
            arg = str(parameterValue)
            arg = arg.replace('[index]', str(index)) if index is not None else arg
            arg = arg.replace('[node_folder]', str(self.getWorkflowDataPath() / self.name))
            arg = arg.replace('[workflow_folder]', str(self.getWorkflowDataPath()))
            arg = Path(arg)
        args[parameterName] = arg
        return
    
    def parameterIsUndefinedAndRequired(self, parameterName, inputs, row=None):
        return any([toolInput.get('required') and self.getParameter(parameterName, row) is None for toolInput in inputs if toolInput['name'] == parameterName])
    
    def setOutputArgsFromDataFrame(self, args, outputData, index):
        if outputData is None: return
        for outputName, output in self.parameters['outputs'].items():
            if self.getColumnName(outputName) not in outputData.columns: continue # sometimes the output column is not defined, as in LabelStatistics ; since it is only used for the image format, and compute() is not called
            outputPath = outputData.at[index, self.getColumnName(outputName)]
            if output['dataType'] == 'Path':
                outputPath = Path(outputPath)
                outputPath.parent.mkdir(exist_ok=True, parents=True)    
            args[outputName] = outputPath

    def getParameter(self, name, row):
        if name not in self.parameters['inputs']: return None
        parameter = self.parameters['inputs'][name]
        return parameter['value'] if parameter['type'] == 'value' else row[parameter['columnName']] if row is not None and parameter['columnName'] in row else None
    
    def getArgs(self, dataFrame: pandas.DataFrame | None, objectify=False, raiseRequiredException=True):
        argsList = []
        if dataFrame is None or len(dataFrame) == 0:
            args = {}
            for parameterName, parameter in self.parameters['inputs'].items():
                if self.parameterIsUndefinedAndRequired(parameterName, self.tool.inputs) and raiseRequiredException:
                    raise Exception(f'The parameter {parameterName} is undefined, but required.')
                self.setArg(args, parameterName, parameter, parameter['value'], None)
            self.setOutputArgsFromDataFrame(args, dataFrame, 0)
            argsList.append(args)
        else:
            for index, row in dataFrame.iterrows():
                args = {}
                for parameterName, parameter in self.parameters['inputs'].items():
                    if self.parameterIsUndefinedAndRequired(parameterName, self.tool.inputs, row) and raiseRequiredException:
                        raise Exception(f'The parameter {parameterName} is undefined, but required.')
                    self.setArg(args, parameterName, parameter, self.getParameter(parameterName, row), index)
                self.setOutputArgsFromDataFrame(args, dataFrame, index)
                if getattr(self.tool, 'setRowInArgs', False):
                    args['idf_row'] = row
                argsList.append(args)
        return [DictToObject(args) for args in argsList] if objectify else argsList



# Manage outputs
            
    def getColumnName(self, parameterName):
        return self.name + ': ' + parameterName
    
    def getStem(self, filename):
        return Path(filename).stem
    
    def getAbsoluteStem(self, filename):
        filename = Path(filename)
        suffixes = "".join(filename.suffixes)
        return str(filename.name)[:-len(suffixes)]
    
    def getSuffixes(self, filename):
        return filename[filename.index('.'):] if '.' in filename else ''

    # Check for {inputName}|.stem|.name.|.parent.name|.ext|.exts and replace by the real input value|file stem|file name|parent folder name|extension|extensions
    def replaceInputArgs(self, outputValue, inputGetter):
        inputGetterStr = lambda name: str(inputGetter(name))
        for name in re.findall(r'\{([a-zA-Z0-9_-]+)\}', outputValue):
            input = inputGetterStr(name)
            if input is not None:
                outputValue = outputValue.replace(f'{{{name}}}', str(input))
        for name in re.findall(r'\{([a-zA-Z0-9_-]+).stem\}', outputValue):
            input = inputGetterStr(name)
            if input is not None:
                outputValue = outputValue.replace(f'{{{name}.stem}}', self.getStem(input))
        for name in re.findall(r'\{([a-zA-Z0-9_-]+).astem\}', outputValue):
            input = inputGetterStr(name)
            if input is not None:
                outputValue = outputValue.replace(f'{{{name}.astem}}', self.getAbsoluteStem(input))
        for name in re.findall(r'\{([a-zA-Z0-9_-]+).name\}', outputValue):
            input = inputGetterStr(name)
            if input is not None:
                outputValue = outputValue.replace(f'{{{name}.name}}', str(Path(input).name))
        for name in re.findall(r'\{([a-zA-Z0-9_-]+).parent.name\}', outputValue):
            input = inputGetterStr(name)
            if input is not None:
                outputValue = outputValue.replace(f'{{{name}.parent.name}}', str(Path(input).parent.name))
        for name in re.findall(r'\{([a-zA-Z0-9_-]+).ext\}', outputValue):
            input = inputGetterStr(name)
            if input is not None:
                outputValue = outputValue.replace(f'{{{name}.ext}}', Path(input).suffix)
        for name in re.findall(r'\{([a-zA-Z0-9_-]+).exts\}', outputValue):
            input = inputGetterStr(name)
            if input is not None:
                outputValue = outputValue.replace(f'{{{name}.exts}}', ''.join(Path(input).suffixes))
        return outputValue

    def replaceOutputKeywords(self, value, outputName, output, row, index):
        finalValue = str(value)
        
        # Check that [workflow_folder] and [node_folder] are used at the beginning of the finalValue (if used at all)
        for name in ['[workflow_folder]', '[node_folder]']:
            if name in finalValue and not finalValue.startswith(name):
                raise Exception(f'Error: the special string "{name}" can only be used at the beginning of the output {outputName}.')
        
        # Check for {inputName}|.stem|.name.|.parent.name|.ext|.exts and replace by the real input value|file stem|file name|parent folder name|extension|extensions
        finalValue = self.replaceInputArgs(finalValue, (lambda iname, row=row: self.getParameter(iname, row)) )
        
        # Check for (columnName) and replace by the row value at this column
        for columnName in re.findall(r'\(([a-zA-Z0-9_-]+)\)', finalValue):
            if columnName in row:
                finalValue = finalValue.replace(f'({columnName})', str(row[columnName]))

        # If finalValue is relative but does not contain [workflow_folder] nor [node_folder]: make it relative to the node_folder
        if ('[workflow_folder]' not in finalValue) and ('[node_folder]' not in finalValue) and (not Path(finalValue).is_absolute()):
            finalValue = '[node_folder]/' + finalValue
        
        finalValue = finalValue.replace('[workflow_folder]', str(self.getWorkflowDataPath()))
        finalValue = finalValue.replace('[node_folder]', str(self.getWorkflowDataPath() / self.name))
        finalValue = finalValue.replace('[index]', str(index))
        if output.get('extension') is not None:
            finalValue = finalValue.replace('[ext]', output.get('extension'))
        return finalValue

    def prefixExtensionsWithIndex(self, s):
        pattern = r"(\{\w+\.(exts|ext)\})$"
        result = re.sub(pattern, r"[index]\1", str(s).replace('[ext]', '[index][ext]'))
        suffix = Path(result).suffix
        if '[index]' in result:
            return result
        elif len(suffix)>0:
            return result.replace(suffix, '[index]' + suffix)
        else:
            return result + '[index]'

    def setOutputColumns(self, data):
        if data is None: return
        for outputName, output in self.parameters['outputs'].items():
            if output['dataType'] != 'Path': continue
            columnName = self.getColumnName(outputName)
            series = pandas.Series(data={}, index=data.index, dtype=str)
            irs = data.iterrows() if not data.empty else [(0, None)]
            for index, row in irs:

                if output.get('value') is None:
                    extension = output.get('extension', '') or ''
                    series.at[index] = self.getWorkflowDataPath() / self.name / f'{outputName}_{index}{extension}'
                else:
                    series.at[index] = self.replaceOutputKeywords(output['value'], outputName, output, row, index)
                
            # Remove duplicates by adding [index] before the file extension
            irs = data.iterrows() if not data.empty else [(0, None)]
            for index, row in irs:
                value = series.at[index]
                # If the value appears more than once in the row: suffix it with index
                if series.value_counts()[value] > 1:
                    data.at[index, columnName] = self.replaceOutputKeywords(self.prefixExtensionsWithIndex(output['value']), outputName, output, row, index)
                else:
                    data.at[index, columnName] = value



# Manage DataFrames

    def mergeDataFrames(self, dataFrames):
        if len(dataFrames)==0: return pandas.DataFrame()
        result = pandas.concat(dataFrames, axis=1)
        # Remove duplicated columns
        result = result.loc[:,~result.columns.duplicated()].copy()
        # Replace every NaN with the first non-NaN value in the same column above it.
        # propagate[s] last valid observation forward to next valid
        result = result.ffill()
        return result

    # Create a dataFrame from the parameters
    def createDataFrameFromParameters(self):
        # return pandas.DataFrame({key: [value['value']] for key, value in self.parameters['inputs'].items()})
        return pandas.DataFrame({})
    
    # update the parameters['inputs'] from data (but do not overwrite parameters['inputs'] which are already column names):
    # for all inputs which are auto, set the corresponding parameter to the column name
    def setParametersFromDataframe(self, data):
        n = len(data.columns)-1 if isinstance(data, pandas.DataFrame) else -1
        for input in self.tool.inputs:
            inputName = input['name']
            parameter = self.parameters['inputs'][inputName]
            if not input.get('autoColumn'): continue
            if isinstance(data, pandas.DataFrame) and len(data)>0:
                paramIsAbsentColumn = parameter['type'] == 'columnName' and parameter['columnName'] not in data.columns
                paramIsUndefinedValue = parameter['type'] == 'value' and parameter.get('value') in [None, '']
                if paramIsAbsentColumn or paramIsUndefinedValue:
                    parameter['type'] = 'columnName'
                    parameter['columnName'] = data.columns[max(0, n)]
                    n -= 1
            elif parameter['type'] == 'columnName':
                parameter['type'] = 'value'

    def getInputDataFrame(self, dataFrames: list[pandas.DataFrame]):
        hasMergeDataFrames = callable(getattr(self.tool, 'mergeDataFrames', None))
        self.inputDataFrame = self.tool.mergeDataFrames(dataFrames, self.getArgs(dataFrame=None, objectify=True, raiseRequiredException=False)) if hasMergeDataFrames else self.mergeDataFrames(dataFrames)
        self.setParametersFromDataframe(self.inputDataFrame)
        return self.inputDataFrame

    def setOutputMessage(self):
        if hasattr(self.tool, 'outputMessage'):
            self.outputMessage = self.tool.outputMessage

    def processDataFrame(self, dataFrames: list[pandas.DataFrame], parameters: dict[str, Any]):
        print(f'------------compute: {self.name}')
        for key, value in parameters.items():
            if not isinstance(value, dict) or "type" not in value:
                value = dict(type="value", value=value)
            for paramType in ["inputs", "outputs"]:
                if key in self.parameters[paramType]:
                    self.parameters[paramType][key].update(value)
        self.inputDataFrame = self.getInputDataFrame(dataFrames)
        self.processedDataFrame = self.tool.processDataFrame(self.inputDataFrame, self.getArgs(self.inputDataFrame, objectify=True, raiseRequiredException=False)) if callable(getattr(self.tool, 'processDataFrame', None)) else self.inputDataFrame.copy()
        if self.processedDataFrame.empty:
            self.processedDataFrame = self.createDataFrameFromParameters()
        self.setOutputColumns(self.processedDataFrame)
        self.setOutputMessage()
        self.setOutputAndClean(self.processedDataFrame)
        self.regenerateThumbnails(self.processedDataFrame)
        return self.processedDataFrame


# Process data

    def processData(self, inputDataFrames:list[pandas.DataFrame], parameters: dict[str, Any]):
        processedDataFrame = self.processDataFrame(inputDataFrames, parameters)
        additionalInstallCommands = getattr(self.tool, 'additionalInstallCommands', [])
        additionalActivateCommands = getattr(self.tool, 'additionalActivateCommands', [])
        environment = self._environment_manager.create(self.tool.environment, self.tool.dependencies, additionalInstallCommands=additionalInstallCommands)
        if isinstance(environment, ExternalEnvironment) and not environment.launched():
            environment.launch(additionalActivateCommands=additionalActivateCommands)
        argsList = self.getArgs(processedDataFrame, objectify=False, raiseRequiredException=True)
        outputFolderPath = self.getOutputDataFolderPath()

        toolLauncherPath = Path(__file__).parent / "tool_launcher.py"
        
        importRootPath = self.getToolParentPath()
        dataFrames:list[pandas.DataFrame | None] = [None] * len(argsList)
        if self.tool.environment != 'bioimageit':
            dataFrames = environment.execute(toolLauncherPath.resolve(), 'processAllData', (str(self.importPath), argsList, outputFolderPath, importRootPath)) or dataFrames
        elif self.tool is not None and hasattr(self.tool, 'processAllData') and callable(self.tool.processAllData):
            dataFrames = cast(list[pandas.DataFrame | None], self.tool.processAllData(DictToObject(argsList))) or dataFrames

        for i, args in enumerate(argsList):
            # The following log will also update the progress bar
            # self.__class__.log.send(f'Process row [[{i+1}/{len(argsList)}]]')
            if self.tool.environment != 'bioimageit':
                dataFrames[i] = environment.execute(toolLauncherPath.resolve(), 'processData', (str(self.importPath), args, outputFolderPath, importRootPath))
            elif self.tool is not None and hasattr(self.tool, 'processData') and callable(self.tool.processData):
                dataFrames[i] = cast(pandas.DataFrame, self.tool.processData(DictToObject(args)))

        self.setOutputMessage()
        dataFrames = [df for df in dataFrames if df is not None]
        if len(dataFrames)==0:
            dataFrames = [processedDataFrame]
        dataFrame = pandas.DataFrame()
        dataFrame = pandas.concat(dataFrames)
        self.setOutputAndClean(dataFrame)
        self.finishExecution(argsList, dataFrame)
        return dataFrame
    
    def getWorkflowDataPath(self):
        return self.workflowPath / 'Data'
    
    def getWorkflowToolsPath(self):
        return self.workflowPath / 'Tools'

    def getOutputDataFolderPath(self):
        return self.workflowPath / 'Data' / self.name

    def getOutputMetadataFolderPath(self):
        return self.workflowPath / 'Metadata' / self.name
    
    def getToolParentPath(self):
        return self.getWorkflowToolsPath() if self.workflowTool else get_root_path()
    
    def saveArgsList(self, argsList, outputFolder):
        if argsList is None: return
        with open(outputFolder / PARAMETERS_PATH, 'w') as f:
            json.dump(argsList, f, default=lambda value: value.to_json(default_handler=str) if callable(getattr(value, 'to_json', None)) else str(value))

    def loadArgsList(self):
        outputFolder = self.getOutputMetadataFolderPath()
        with open(outputFolder / PARAMETERS_PATH, 'r') as f:
            return json.load(f)
    
    def loadProcessedDataFrame(self):
        outputFolder = self.getOutputMetadataFolderPath()
        return pandas.read_csv(outputFolder / OUTPUT_DATAFRAME_PATH)
    
    def finishExecution(self, argsList: list[Any], dataFrame: pandas.DataFrame | None):
        outputFolder = self.getOutputMetadataFolderPath()
        outputFolder.mkdir(exist_ok=True, parents=True)

        self.regenerateThumbnails(dataFrame)

        if dataFrame is not None:
            dataFrame.to_csv(outputFolder / OUTPUT_DATAFRAME_PATH, index=False)
        
        self.saveArgsList(argsList, outputFolder)
        self.setExecuted(True)

    def clear(self):
        self.deleteFiles()
        self.setExecuted(False, setDirty=True)
    
    def setExecuted(self, executed=True, setDirty=True):
        if not executed and setDirty:
            self.inputDataFrame = None
            self.processedDataFrame = None
        self.executed = executed
    
    def regenerateThumbnails(self, dataFrame):
        # self.deleteThumbnails()
        # ThumbnailGenerator.get().generateThumbnails(self.name, dataFrame)
        pass

    def deleteThumbnails(self):
        # ThumbnailGenerator.get().deleteThumbnails(self.name)
        pass
    
    def deleteFiles(self):
        self.deleteThumbnails()
        for outputFolder in [self.getOutputDataFolderPath(), self.getOutputMetadataFolderPath()]:
            if outputFolder.exists():
                send2trash(outputFolder)

    def setOutputAndClean(self, data):
        # self.dirty = False
        # self.outputDataFrame = data
        pass
