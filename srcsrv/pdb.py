'''
    Program Database (PDB) parsing and modifying class
'''

# Copyright (C) 2019-2023 Uri Mann (abba.mann@gmail.com)

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
import re
import json
import time
import logging
import subprocess


class PDB:
    '''.PDB processing
    '''
    def __init__(self, si, pdb_path):
        super(PDB, self).__init__()
        self.si = si
        self._sources_count = 0
        self._pdb_path = pdb_path
        self._ini_path = self._pdb_path[:-4] + '.ini'
        self._srcs_path = self._pdb_path[:-4] + '.srcs'
 
    def sources(self, srcs_match):
        '''
        Property containing a list of source files in the current source tree
        :return List of source files
        '''
        # Send the output to a file. On large .PDBs with many entries
        # using OS buffering consumes too much time and memory.
        with open(self._srcs_path, 'w+') as srcs:
            cmd = [
                self.si.srctool,
                f'-l:{srcs_match}*',
                '-r', '-z', '-h',
                self._pdb_path
            ]

            try:
                cp = subprocess.run(cmd, stdout=srcs, check=True)
                srcs.seek(0)
                yield from srcs
            except subprocess.CalledProcessError as ex:
                if ex.stderr:
                    logging.error(f'{cmd=} returned error 0x{ex.returncode:08x}! stdout: "{ex.stdout}", stderr: "{ex.stderr}"')

    def process(self):
        '''
        Process a single .PDB file
        '''
        start = time.time()
        summary = {
            'pdb': self._pdb_path,
        }

        with open(self._ini_path, 'w') as stream:
            # Write metadata
            stream.write(
rf'''
SRCSRV: ini ------------------------------------------------
VERSION=2
VERCTRL=
SRCSRV: variables ------------------------------------------
SRCSRVTRG={self.si.args.cache}/%var4%/%var3%
'''
            )

            # Write VARIABLES section of SRCSRV.ini
            self.si.args.plugin.header(stream)

            # Start of .PDB entries database
            stream.write(
'''SRCSRV: source files ---------------------------------------
'''
            )

            # create RegEx for source files
            exts = '|'.join(self.si.args.extensions.split(';'))
            srcs_match = re.sub(r'\\', r'\\\\', self.si.args.build_base)
            entry_regex = '(' + srcs_match + rf'.+\.({exts}))\t Checksum (MD5|SHA256): ([A-Fa-f0-9]+)'

            for source_entry in self.sources(srcs_match):
                match = re.match(entry_regex, source_entry, re.IGNORECASE)
                if not match: continue

                file_pdb_path = match.group(1)
                file_pdb_hash = match.group(4)
                try:
                    # find matching repository file
                    blob = self.si.sources[file_pdb_path]
                except KeyError:
                    logging.warning(f'Could not found {file_pdb_path} in {self._pdb_path}')
                    continue

                # Write source file item to SRCSRV.ini
                if not self.si.args.plugin.entry(stream=stream,
                                                file_build_path=file_pdb_path,
                                                file_pdb_hash=file_pdb_hash,
                                                file_path=blob.file_path,
                                                file_name=blob.file_name,
                                                file_repo_hash=blob.file_repo_hash):
                    logging.warning(f'Failed entry into {self._pdb_path}')
                    return False
                self._sources_count = self._sources_count + 1

            # Q: Were any entries written to the stream?
            if self._sources_count == 0:
                if self.si.args.summary:
                    # Summarize execution
                    summary.update(
                            {
                                'duration': time.time() - start,
                            }
                        )
                    json.dump(summary, self.si.args.summary, indent='  ')

                stream.close()
                os.remove(self._ini_path)
                os.remove(self._srcs_path)
                logging.warning(f'{self._pdb_path} no source files found')
                return False

            # End of .PDB entries database
            stream.write(
'''SRCSRV: end ------------------------------------------------
'''
            )

        logging.info(f'{self._pdb_path} contains: {self._sources_count} source files')
        # Write the the output file onto the .PDB
        if not self.si.args.dry_run:
            cmd = [
                self.si.pdbstr,
                '-w',
                f'-p:{self._pdb_path}',
                '-s:srcsrv',
                f'-i:{stream.name}'
            ]

            try:
                cp = subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as ex:
                logging.error(f'{cmd=} returned error 0x{ex.returncode:08x}! stdout: "{ex.stdout}", stderr: "{ex.stderr}"')

        if not self.si.args.keep:
            # Remove the output files
            os.remove(self._ini_path)
            os.remove(self._srcs_path)

        if self.si.args.summary:
            if self.si.args.level[0] == 'v':
                # Verbose summary of execution
                summary.update(
                        {
                            'sources': list(self.sources.items()),
                            'duration (seconds)': time.time() - start,
                        }
                    )
            if self.si.args.level[0] == 'd':
                # Detailed summary of execution
                summary.update(
                        {
                            'sources': len(self.sources.items()),
                            'duration (seconds)': time.time() - start,
                        }
                    )
            elif self.si.args.level[0] == 'n':
                # Normal summary of execution
                summary.update(
                        {
                            'duration (seconds)': time.time() - start,
                        }
                    )
            elif self.si.args.level[0] == 'm':
                return True

            json.dump(summary, self.si.args.summary, indent='  ')

        return True


__all__ = ['PDB']
