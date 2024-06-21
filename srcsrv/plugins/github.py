'''
    Github processing plugin
    This module facilitate processing and fetching files from Github and Github Enterprise
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
import io
import os
import requests
import argparse
import logging
# Source index modules
from . import plugin
from .. import utils


class Github(plugin.Plugin):
    '''
    Github processing plugin
    This module facilitate processing and fetching files from Github and Github Enterprise
    '''

    AUTH = 'SRCSRV_GITHUB_AUTH'

    def __init__(self, args=None, unparsed_args: argparse.Namespace=None):
        '''
        Github plugin constructor

        Params:
        args - All currently parsed arguments
        unparsed_args - Remaining arguments to parse
        '''

        # Add plugin specific arguments
        parser = argparse.ArgumentParser(allow_abbrev=False)

        parser.add_argument('-u', '--account', help='Repository account', default='%SRCSRV_USERNAME%')
        parser.add_argument('-r', '--repo',    help='Repository name',    required=True)

        super().__init__(parser=parser, args=args, unparsed_args=unparsed_args)

    @staticmethod
    def route(account, repo, file_path, file_name):
        '''
        Routing for mocking github REST API
        https://docs.github.com/en/rest/overview/media-types#raw-media-type-for-repository-contents
        https://docs.github.com/en/rest/repos/contents#get-repository-content
        '''
        repo_path = f'{file_path}/{file_name}'
        ref = flask.request.args.get('ref')
        logging.info(flask.request.headers)
        logging.info(f'{flask.request.host_url}:'\
                     f'{account}/{repo}/{repo_path}?'\
                     f'{ref}')

        with utils.GitGuard(Github.repo, commit=ref) as gg:
            blob_id = gg.repo.git.hash_object(repo_path)
            # https://git-scm.com/docs/git-cat-file
            return gg.repo.git.cat_file(['blob', blob_id])

    @classmethod
    def initialize(cls, app) -> bool:
        '''
        Initialize before first debugging session

        Params:
        app - Flask app simulating Github REST API service
        '''
        # In order for the overall package not to have dependencies which are
        # only needed for testing, importing is done during initialization
        global flask
        import git
        import flask
        app.route('/repos/<account>/<repo>/contents/<path:file_path>/<file_name>',
                  subdomain='api.github', methods=['GET',])(Github.route)
        cls.app = app
        cls.working_dir = os.path.join(app.instance_path, 'test', 'repos', 'github')
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
                    '--account': self.args.account,
                    '--repo':    self.args.repo,
                    '--auth':    auth,
                }
            )

    def header(self, stream) -> bool:
        '''
        Write SRCSRV.ini header

        Parameters:
            stream - SRCSRV.ini stream to write to
        '''
        content = rf'''
SRCSRVCMD={self.args.python} -c "import srcsrv;srcsrv.main([%gh_plugin%,%gh_uri%,%gh_acct%,%gh_repo%,%gh_commit%,%gh_verify%,r'-c=%SRCSRVTRG%']).fetch('%var2%','%var3%','%var4%')"
GH_BASE={self.args.build_base}
GH_PLUGIN='-$=srcsrv.plugins.Github'
GH_URI='-@={self.args.uri}'
GH_COMMIT='-#={self.args.commit}'
GH_VERIFY='-v={self.args.verify}'
GH_ACCT='-u={self.args.account}'
GH_REPO='-r={self.args.repo}'
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
        return super(Github, self).entry(stream=stream,
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
            # https://docs.github.com/en/rest/overview/media-types#raw-media-type-for-repository-contents
            'Accept': 'application/vnd.github.raw',
        }

        auth = utils.get_authorization(auth_var=self.AUTH, headers=headers)

        # compose REST API call
        # https://docs.github.com/en/rest/repos/contents#get-repository-content
        params = { 'ref': self.args.commit }
        rest_api_call = f'https://api.{self.args.uri}/repos/'\
                        f'{self.args.account}/'\
                        f'{self.args.repo}/'\
                        f'contents{file_path}'\
                        f'{file_name}'

        # fetch the source from the repo
        response = requests.get(rest_api_call,
                                headers=headers,
                                auth=auth,
                                params=params,
                                verify=self.args.verify)
        return super(Github, self).fetch(file_path=file_path,
                                         file_name=file_name,
                                         file_pdb_hash=file_pdb_hash,
                                         response=response,
                                         rest_api_call=rest_api_call,
                                         file_description=f'{self.args.account}/'\
                                                          f'{self.args.repo}')


__all__ = ['Github']
