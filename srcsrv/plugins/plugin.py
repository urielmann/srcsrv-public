'''
    Plugin interface
'''
    
# Copyright (C) 2023 Uri Mann (abba.mann@gmail.com)

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
import io
import os
import abc
import sys
import logging
import argparse

class Plugin(abc.ABC):
    '''
    srcsrv plugin interface definition
    '''
    @abc.abstractmethod
    def __init__(self, parser=None, args=None, unparsed_args: argparse.Namespace=None):
        '''
        Github plugin constructor

        Params:
        parser - Parser instance
        args - All currently parsed arguments
        unparsed_args - Remaining arguments to parse
        '''
        super(abc.ABC, self).__init__()
        self.args = args

        logging.info(unparsed_args)
        if parser:
            # Parse remaining  unrecognized args
            namespace = parser.parse_args(unparsed_args)
            # Combine the arguments lists
            self.args.__dict__.update(namespace.__dict__)


    @classmethod
    @abc.abstractmethod
    def initialize(cls, cache) -> bool:
        '''
        Initialize before first debugging session
        '''
        pass

    @abc.abstractmethod
    def header(self, stream) -> bool:
        '''
        Write SRCSRV.ini header

        Parameters:
            stream - SRCSRV.ini stream to write to
        '''
        pass

    @abc.abstractmethod
    def add_arguments(self, arguments:dict) -> None:
        '''
        Add plugin arguments to summary

        Parameters:
            arguments - Dictionary to append arguments to
        '''
        pass

    @abc.abstractmethod
    def entry(self, stream: io.TextIOBase,
                    file_build_path: str,
                    file_path: str,
                    file_name: str,
                    file_pdb_hash: str,
                    file_repo_hash: str) -> bool:
        '''
        Write SRCSRV.ini source file entry

        Parameters:
            stream - SRCSRV.ini stream to write to
            file_build_path - Source file path build in .PDB
            repo_path - Repo entry path
            file_pdb_hash - Content hash from .PDB
            file_repo_hash - Repo hash of the file
        '''
        line = f'{file_build_path}*{file_path}*{file_name}*{file_pdb_hash}*{file_repo_hash}'
        stream.write(f'{line}\n')
        logging.info(line)
        return True

    @abc.abstractmethod
    def fetch(self, file_path: str,
                    file_name: str,
                    file_pdb_hash: str,
                    *args, **kwargs) -> bool:
        '''
        Fetch source file

        Parameters:
            file_path - Relative path to source file
            file_name - Source file name
            file_pdb_hash - MD5 or SHA256 digest of the file
            file_repo_hash - MD5 of the source file
        '''

        rest_api_call = kwargs["rest_api_call"]
        file_description = kwargs["file_description"]
        response = kwargs['response']
        if response.status_code != 200:
            logging.error(f'REST API call: {rest_api_call}: error {response.status_code}: {response.content}')
            sys.exit(1)

        logging.info(f'REST API call: {rest_api_call}')

        # Add cache directory
        cache_dir = os.path.join(self.args.cache, file_pdb_hash)
        cache_file = os.path.join(cache_dir, file_name)
        os.makedirs(cache_dir, exist_ok=True)

        # Add entry to inventory file
        inventory_dir = os.path.join(cache_dir, '.inv')
        inventory_file = os.path.join(inventory_dir, 'inv.txt')
        os.makedirs(inventory_dir, exist_ok=True)
        with open(inventory_file, 'a+') as inv:
            entry = f'{file_name}: {self.args.uri}/{file_description}'\
                    f'{file_path}{file_name}:{self.args.commit}\n'

            inv.seek(0, 0)
            lines = inv.readlines()
            empty = len(lines) == 0
            file_name_found = False
            if empty:
                inv.write(f'# Ver: 1.0 - Cache inventory {file_pdb_hash}\n')
            else:
                # Check if the file is already in the inventory
                for line in lines:
                    # Q: Does such entry exists in the inventory file?
                    if line.lower() == entry.lower():
                        logging.info(f'{file_name}: already cached')
                        return True

                    # Q: Is the file with the same name already cached?
                    if line.lower().startswith(f'{file_name.lower()}:'):
                        file_name_found = True

            if file_name_found:
                # File with the same name is inventory but from a different
                # path or commit
                logging.info(f'adding to inventory {entry}')
                inv.seek(0, 2)
                inv.write(entry)
                return True

            logging.info(entry)
            # Add to inventory
            inv.write(entry)
            
            # Q: Does the file content exists under different name?
            if not empty:
                line = lines[1]
                end_src_name = line.find(':', 0)
                src_name =  line[:end_src_name]
                src_path = os.path.join(cache_dir, src_name)
                os.link(src_path, cache_file)                
                return True

        # add to cache
        with open(cache_file, 'wb') as cf:
            cf.write(response.text.encode())

        logging.info(f'{cache_file}: {self.args.uri}/{file_description}'\
                     f'{file_path}{file_name}')

        return True

__all__ = ['Plugin']
