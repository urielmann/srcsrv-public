'''
    Scrip for source indexing
'''

# Copyright (C) 2019-2023 Uriel Mann (abba.mann@gmail.com)

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Python modules
import os
import git
import sys
import pip
import json
import datetime
import logging
import argparse
import importlib
# Source index modules
from . import indexer
from . import utils


def main(argv=sys.argv[1:]):
    '''
    Main entry point
    '''
    class ArgumentParser(argparse.ArgumentParser):
        '''
        Arguments parsing class
        '''

        def parse_known_args(self, args=None, namespace=None):
            '''
            Parse common arguments and pass remaining args to plugin for parsing
            '''
            namespace, args = super(ArgumentParser, self).parse_known_args(args, namespace)
            if len(args) == 0 and type(namespace.plugin) != str:
                # No plugin specific arguments found
                return namespace, args

            # Validate plugin class
            try:
                # Separate between the module and class name
                module, klass = namespace.plugin.rsplit('.', 1)
                mdl = importlib.import_module(module)
                # 'plugin' attribute is now the class type
                namespace.plugin = getattr(mdl, klass)
            except ValueError as err:
                error = f'{args.plugin} does not look like a module path'
                logging.exception(error, stack_info=True)
                raise ImportError(error) from err
            except AttributeError as err:
                error = f'Module {module} does not define a {klass} attribute/class'
                logging.exception(error, stack_info=True)
                raise ImportError(error) from err

            # Instantiate plugin which will parse specific argument onto 'namespace'
            namespace.plugin = namespace.plugin(namespace, args)
            return namespace, []

    def parse_general_args(args):
        '''
        Parse general arguments
        '''
        parser = ArgumentParser(allow_abbrev=False)

        # General options
        parser.add_argument('-!', '--action',     help='Action type (index, fetch)', default=utils.ValidateAction.FETCH,
                                                  type=utils.ValidateAction.argparse, choices=list(utils.ValidateAction))
        parser.add_argument('-@', '--uri',        help='Git repository server URI',
                                                  default='github.com', action=ValidateUri, required=True)
        parser.add_argument('-$', '--plugin',     help='Plugin class',
                                                  default='srcsrv.plugins.Github')
        parser.add_argument('-#', '--commit',     help='Git repository commit hash', action=ValidateCommit)

        # Indexing options
        parser.add_argument('-b', '--build-base', help='Build directory path',
                                                  default=os.getcwd(), action=ValidateBuildBase)
        parser.add_argument('-x', '--extensions', help='Semicolon separated list of source extensions (default: cpp;hpp;c;h)',
                                                  default='cpp;hpp;c;h')
        parser.add_argument('-s', '--srcsrv',     help='SRCSRV tools directory',
                                                  default=r'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\srcsrv')
        parser.add_argument('-p', '--pdbs',       help='Paths to .PDB directories', nargs='+', default=['.'])

        # Fetch options
        parser.add_argument('-e', '--python',     help='Python executable', default='py.exe')
        parser.add_argument('-c', '--cache',      help='Source cache directory')
        parser.add_argument('-v', '--verify',     help='Verify server certificate. Set to False to skip',
                                                  default=None, type=lambda x: False if x.lower()=='false' else None)

        # Diagnosis options
        parser.add_argument('-k', '--keep',       help='Keep temporary artifacts', action='store_true')
        parser.add_argument('-n', '--dry-run',    help='Do not change .PDB files',
                                                  default=None, choices=(None, 'True', 'False', '1', '0'))
        parser.add_argument('-m', '--summary',    help='Path to performance summary file',
                                                  default=None, type=argparse.FileType('w'))
        parser.add_argument('-q', '--level',      help='Level of details of performance summary file',
                                                  default='minimal', choices=['m', 'minimal', 'n', 'normal', 'd', 'detailed', 'v', 'verbose'])
        parsed_args = parser.parse_args(args=args)

        return parsed_args

    class DebugArgumentParser(argparse.ArgumentParser):
        '''
        Arguments parsing class for debug option. This class is doing initial arg parsing
        just to check if debug flag is set. If it is, it will trigger a break point before
        parsing the rest of the command line arguments.
        '''

        def convert_arg_line_to_args(self, arg_line):
            '''
            Allow parameter file to have whitespace separators
            '''
            return arg_line.split()

        def parse_known_args(self, args=None, namespace=None):
            '''
            Parse debug argument and pass remaining args to plugin for parsing
            '''
            parsed_args, unparsed_args = super(DebugArgumentParser, self).parse_known_args(args, namespace)

            if parsed_args.debug:
                # Attach debugger
                try:
                    import debugpy
                except:
                    pip.main(['install', '--upgrade', 'debugpy'])
                    import debugpy

                debugpy.listen(5678, in_process_debug_adapter=True)
                print("Waiting for debugger to attach")
                debugpy.wait_for_client()
                debugpy.breakpoint()
                print('Stopped')

            # Initialize logging
            if parsed_args.log:
                level = logging.INFO
            else:
                level = None
            logging.basicConfig(stream=parsed_args.log,
                                level=level,
                                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            # parse general arguments. Any unparsed arguments are also passed to the
            # plugin to parse plugin specific arguments.
            all_args = parse_general_args(args=unparsed_args)
            # combine the full argument list. This list contains both the debug flag,
            # general arguments, and the plugin specific arguments.
            parsed_args.__dict__.update(all_args.__dict__)

            return parsed_args, []

    class ValidateUri(argparse.Action):
        '''
        Uri validation
        '''
        def __init__(self, option_strings, dest, nargs=None, **kwargs):
            super(ValidateUri, self).__init__(option_strings, dest, **kwargs)

        def __call__(self, parser, namespace, value, option_string=None):
            # Make sure the uri does not start with 'https://'
            if value.startswith('https://'):
                value = value[8:]
            # Make sure the uri is just the sever name
            pos = value.find('/')
            if pos > 0:
                value = value[:pos]
            setattr(namespace, self.dest, value)

    class ValidateCommit(argparse.Action):
        '''
        Validate and store 'commit'
        '''
        def __init__(self, option_strings, dest, nargs=None, **kwargs):
            super(ValidateCommit, self).__init__(option_strings, dest, **kwargs)

        def __call__(self, parser, namespace, value, option_string=None):
            '''
            Validate commit argument formatted correctly
            '''
            if namespace.action == utils.ValidateAction.FETCH:
                # No validation of commit for fetching
                setattr(namespace, self.dest, value)
                return

            try:
                if not value or len(value) != 40:
                    raise ValueError
                int(value, 16)
            except ValueError:
                try:
                    # default is the local repo current commit
                    repo = git.Repo(namespace.build_base)
                    # default to current commit if no value provided
                    if not value:
                        value = repo.active_branch.object.hexsha
                    # This could be a tag
                    elif value not in repo.tags:
                        error = f'Commit {value} not found'
                        logging.exception(error, stack_info=True)
                        raise ValueError(error)
                except git.GitError:
                    pass
            setattr(namespace, self.dest, value)

    class ValidateBuildBase(argparse.Action):
        '''
        Base class for source indexing
        '''
        def __init__(self, option_strings, dest, nargs=None, **kwargs):
            super(ValidateBuildBase, self).__init__(option_strings, dest, **kwargs)

        def __call__(self, parser, namespace, value, option_string=None):
            '''
            Validate build_base is backslash terminated
            '''
            value = os.path.normpath(value)
            # Make sure the path ends with '\\'
            if not value.endswith('\\'):
                value = value + '\\'
            setattr(namespace, self.dest, value)

    # Configuration file with command line parameters
    # @NOTE: Any command line switch can be added to configuration file
    #        if it appears later on the command line
    parser = DebugArgumentParser(fromfile_prefix_chars='@', allow_abbrev=False)

    # Debugging and logging options
    parser.add_argument('-d', '--debug', help='Attache debugger',
                                         default=False, action='store_true')
    parser.add_argument('-l', '--log',   help='Path to log file (default: stdout)',
                                         default=None, type=argparse.FileType('w'))
    args = parser.parse_args(args=argv)

    # Normalize the path
    args.build_base = os.path.normpath(args.build_base) + '\\'

    # Set default commit if not provided
    if not args.commit:
        repo = git.Repo(args.build_base)
        args.commit = repo.active_branch.object.hexsha

    if args.dry_run:
        if args.dry_run.lower() == 'true' or args.dry_run == '1':
            args.dry_run = True
        elif args.dry_run.lower() == 'false' or args.dry_run == '0':
            args.dry_run = False

    if args.summary:
        # Summarize arguments
        arguments = {
            'date':         datetime.datetime.isoformat(datetime.datetime.today()),
            '--debug':      args.debug,
            '--action':     str(args.action),
            '--uri':        args.uri,
            '--plugin':     f'{args.plugin.__module__}.{args.plugin.__class__.__qualname__}',
            #'--log':        args.log.__name__,
            '--verify':     args.verify,
            '--build-base': args.build_base,
            '--extensions': args.extensions,
            '--srcsrv':     args.srcsrv,
            '--commit':     args.commit,
            '--pdbs':       args.pdbs,
            '--python':     args.python,
            '--keep':       args.keep,
            '--dry-run':    args.dry_run,
            '--cache':      args.cache,
        }
        args.plugin.add_arguments(arguments)
        json.dump(arguments, args.summary, indent='  ')

    if args.action == utils.ValidateAction.INDEX:
        if not args.cache:
            # Get cache directory location from the environment
            args.cache = os.path.join('%USERPROFILE%', '.srcsrv')
        else:
            args.cache = os.path.join(args.cache, '.srcsrv')

        # Normalize the path to forward slash
        args.cache = args.cache.replace('\\', '/')

        return indexer.Indexer(args)
    else:
        #
        # The value of SRCSRVTRG is passed in as the cache value
        #

        path = os.path.normpath(args.plugin.args.cache)
        # Break path to components
        path_parts = path.split(os.sep)

        try:
            # Find the position of the cache dir
            ss_pos = [dir.lower() for dir in path_parts].index('.srcsrv')
        except KeyError:
            error = 'Subdirectory .srcsrv not found in SRCSRVTRG'
            logging.exception(error, stack_info=True)
            raise KeyError(error)

        # Trim off the source subdirectories and source file
        path_parts = path_parts[:ss_pos + 1]
        # Normalize the drive letter
        if ((len(path_parts[0]) == 2 and path_parts[0][1] == ':') or \
            (len(path_parts[0]) == 0)):
            path_parts[0] = path_parts[0] + '\\'
        # Store the path to the cache directory for use by the plugin
        args.plugin.args.cache = os.path.join(*path_parts)

        message = f'SRCSRV cache directory: {args.plugin.args.cache}'

        logging.info(message)
        print(message, file=sys.stderr)

        return args.plugin


if __name__ == '__main__':
    main()
