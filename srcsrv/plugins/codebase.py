'''
    Codebase processing plugin
    This module facilitate processing and fetching files from Github and Github Enterprise
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
import logging
import requests
import argparse
# Source index modules
from . import plugin
from .. import utils


class Codebase(plugin.Plugin):
    '''
    Codebase processing plugin
    This module facilitate processing and fetching files from Codebase
    '''

    AUTH = 'SRCSRV_CODEBASE_AUTH'

    def __init__(self, args=None, unparsed_args: argparse.Namespace=None):
        '''
        Codebase plugin constructor

        Params:
        args - All currently parsed arguments
        unparsed_args - Remaining arguments to parse
        '''

        # Add plugin specific arguments
        parser = argparse.ArgumentParser(allow_abbrev=False)

        parser.add_argument('-i', '--domain',         help='Repository domain',     required=True)
        parser.add_argument('-u', '--account',        help='Repository account',    default='%SRCSRV_USERNAME%')
        parser.add_argument('-t', '--proj-permalink', help='Project permalink',     required=True)
        parser.add_argument('-r', '--repo-permalink', help='Repository  permalink', required=True)
        parser.add_argument('-j', '--api',            help='REST API version',
                                                      default='api3')

        super().__init__(parser=parser, args=args, unparsed_args=unparsed_args)

    def routes(proj_permalink,
               repo_permalink,
               commit,
               file_path,
               file_name):
        '''
        Routing for codebase REST API
        https://support.codebasehq.com/kb/repositories/files
        '''
        repo_path = f'{file_path}/{file_name}'
        logging.info(flask.request.headers)
        logging.info(f'{flask.request.url}:'\
                     f'{proj_permalink}/{repo_permalink}/{commit}/{repo_path}')

        with utils.GitGuard(Codebase.repo, commit=commit) as gg:
            blob_id = gg.repo.git.hash_object(repo_path)
            # https://git-scm.com/docs/git-cat-file
            return gg.repo.git.cat_file(['blob', blob_id])

    @classmethod
    def initialize(cls, app) -> bool:
        '''
        Initialize before first debugging session

        Params:
        app - Flask app simulating Codebase REST API service
        '''
        # In order for the overall package not to have dependencies which are
        # only needed for testing, importing is done during initialization
        global flask
        import git
        import flask

        app.route('/<proj_permalink>/<repo_permalink>/blob/<commit>/<path:file_path>/<file_name>',
                  subdomain='api3.codebase', methods=['GET',])(Codebase.routes)
        cls.app = app
        cls.working_dir = os.path.join(app.instance_path, 'test', 'repos', 'codebase')
        cls.repo = git.Repo(cls.working_dir)
        logging.info(f'{cls.__name__} initialized')

    def add_arguments(self, arguments:dict) -> None:
        '''
        Add plugin arguments to summary

        Parameters:
            arguments - Dictionary to append arguments to
        '''
        # Q: Verbose summary requested?
        if self.args.level[0] == 'v':
            try:
                auth = os.environ[self.AUTH]
            except KeyError:
                auth = 'Not set'

            auth = (self.AUTH, auth)
        else:
            auth = self.AUTH

        arguments.update(
                {
                    '--domain':         self.args.domain,
                    '--account':        self.args.account,
                    '--proj-permalink': self.args.proj_permalink,
                    '--repo-permalink': self.args.repo_permalink,
                    '--auth':           auth,
                }
            )

    def header(self, stream) -> bool:
        '''
        Write SRCSRV.ini header

        Parameters:
            stream - SRCSRV.ini stream to write to
        '''
        content = rf'''
SRCSRVCMD={self.args.python} -c "import srcsrv;srcsrv.main([%cb_plugin%,%cb_uri%,%cb_api%,%cb_domain%,%cb_account%,%cb_project%,%cb_repo%,%cb_commit%,%cb_verify%,r'-c=%SRCSRVTRG%']).fetch('%var2%','%var3%','%var4%')"
CB_BASE={self.args.build_base}
CB_PLUGIN='-$=srcsrv.plugins.Codebase'
CB_URI='-@={self.args.uri}'
CB_COMMIT='-#={self.args.commit}'
CB_VERIFY='-v={self.args.verify}'
CB_DOMAIN='-i={self.args.domain}'
CB_ACCOUNT='-u={self.args.account}'
CB_PROJECT='-t={self.args.proj_permalink}'
CB_REPO='-r={self.args.repo_permalink}'
CB_API='-j={self.args.api}'
'''
        logging.info(content)
        stream.write(content)
        return True

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
            file_path - Relative path to source file
            file_name - Source file name
            file_pdb_hash - MD5 or SHA256 digest of the file
            file_repo_hash - MD5 of the source file
        '''
        return super(Codebase, self).entry(stream=stream,
                                           file_build_path=file_build_path,
                                           file_path=file_path,
                                           file_name=file_name,
                                           file_pdb_hash=file_pdb_hash,
                                           file_repo_hash=file_repo_hash)

    def fetch(self, file_path: str,
                    file_name: str,
                    file_pdb_hash: str) -> bool:
        '''
        Fetch source file

        Parameters:
            file_path - Relative path to source file
            file_name - Source file name
            file_pdb_hash - MD5 or SHA256 digest of the file
        '''
        
        headers = {
            'Accept': 'application/json',
            'Content-type': 'application/json',
        }

        auth = utils.get_authorization(auth_var=self.AUTH, headers=headers)

        # compose REST API call
        params = { 'ref': self.args.commit }
        rest_api_call = f'https://api3.{self.args.uri}/'\
                        f'{self.args.proj_permalink}/'\
                        f'{self.args.repo_permalink}/'\
                        f'blob/{self.args.commit}{file_path}'\
                        f'{file_name}'

        # fetch the source from the repo
        response = requests.get(rest_api_call,
                                headers=headers,
                                auth=auth,
                                params=params,
                                verify=self.args.verify)
        return super(Codebase, self).fetch(file_path=file_path,
                                           file_name=file_name,
                                           file_pdb_hash=file_pdb_hash,
                                           response=response,
                                           rest_api_call=rest_api_call,
                                           file_description=f'{self.args.proj_permalink}/'\
                                                            f'{self.args.repo_permalink}')


__all__ = ['Codebase']
