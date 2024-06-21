'''
    Indexer class
'''

# Copyright (C) 2019 Uri Mann (abba.mann@gmail.com)

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
import json
import time
import argparse
import logging
import pathlib
# Source index modules
from . import pdb
from . import utils


class Indexer:
    '''
    Source indexer class
    '''
    def __init__(self, args):
        super(Indexer, self).__init__()

        self.args = args
        # Validate build path
        if not os.path.isdir(self.args.srcsrv):
            error = f'directory {args.srcsrv} does not exist'
            logging.error(error)
            raise FileNotFoundError(error)
        logging.info(args)

        self._sources = None
        self.srctool = os.path.join(self.args.srcsrv, 'srctool.exe')
        self.pdbstr = os.path.join(self.args.srcsrv, 'pdbstr.exe')
        try:
            self.repo = git.Repo(self.args.build_base)
        except:
            pass

    @property
    def sources(self):
        '''
        Create a list of all source files in the repository
        '''
        if self._sources:
            return self._sources

        class SourceDict:
            '''
            Dictionary mapping .BPD file path to repo attributes of the source file BLOB
            '''
            def __init__(self, args: argparse.Namespace, repo: git.Repo):
                '''
                Initialize the dictionary
                
                Params:
                args - argparse Namespace with all command line arguments
                repo - Current git repository
                '''
                self.sources = {}
                self.args = args
                self.repo = repo

            def __getitem__(self, key):
                '''
                Params:
                key - The full path to a source file with symbols in the .PDB
                '''
                try:
                    return self.sources[key]
                except KeyError:
                    class Blob:
                        def __init__(self, args: argparse.Namespace,
                                           key: str,
                                           file_repo_hash:str):
                            '''
                            Initialize a repo file BLOB
                            
                            Params:
                            args - argparse Namespace with all command line arguments
                            key - The full path to a source file with symbols in the .PDB
                            file_repo_hash - File repo BLOB hash
                            '''
                            file_repo_path = key[len(args.build_base)-1:].replace('\\', '/')
                            file_path = os.path.dirname(file_repo_path)
                            self.file_path = f'{file_path}/' if len(file_path) > 1 else file_path
                            self.file_name = os.path.basename(file_repo_path)
                            self.file_repo_hash = file_repo_hash

                    file_build_path = str(pathlib.Path(key).resolve())
                    file_repo_hash = self.repo.git.hash_object(file_build_path) if self.repo else None
                    self.sources.update({ key: Blob(self.args, file_build_path, file_repo_hash) })
                    return self.sources[key]
        self._sources = SourceDict(self.args, getattr(self, 'repo', None))
        return self._sources

    def _index(self):
        '''
        Generator for path to symbols files
        '''
        for item in self.args.pdbs:
            # item could be a .PDB file or a directory with .PDB files
            if item.endswith('.pdb') and os.path.isfile(item):
                yield item
            elif not os.path.isdir(item):
                logging.error('Directory: {bld_dir} not found')
                continue    # Non-fatal error, skip invalid directory

            for dir, subdirs, files in os.walk(item):
                for fname in files:
                    if fname.endswith('.pdb'):
                        yield os.path.join(dir, fname).replace('\\', '/')

    def index(self):
        '''
        Process each of the .PDBs
        '''

        assert self.args.action == utils.ValidateAction.INDEX

        start = time.time()
        processed = 0
        failed = 0
        for pdb_path in self._index():
            if not pdb.PDB(self, pdb_path).process():
                logging.warning(f'Error processing {pdb_path}')
                failed = failed + 1
            else:
                processed = processed + 1

        if processed == 0:
            logging.warning(f'No files processed')
        if failed > 0:
            logging.warning(f'Failed to process: {failed}')
        logging.info(f'Indexing {self.args.pdbs} completed. Processed: {processed}, Failed: {failed}')

        if self.args.summary:
            # Summarize execution
            summary = {
                'processed': processed,
                'failed':    failed,
                'duration (seconds)':  time.time() - start,
            }
            json.dump(summary, self.args.summary, indent='  ')

        return True

__all__ = ['Indexer']
