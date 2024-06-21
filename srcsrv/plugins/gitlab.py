'''
    Gitlab processing plugin
    This module facilitate processing and fetching files from Gitlab
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
import sys
import logging
import requests
import argparse
# Source index modules
from . import plugin
from .. import utils


class Gitlab(plugin.Plugin):
    '''
    Gitlab processing plugin
    This module facilitate processing and fetching files from Gitlab
    '''

    AUTH = 'SRCSRV_GITLAB_AUTH'

    def __init__(self, args=None, unparsed_args: argparse.Namespace=None):
        '''
        Gitlab plugin constructor

        Params:
        args - All currently parsed arguments
        unparsed_args - Remaining arguments to parse
        '''

        # Add plugin specific arguments
        parser = argparse.ArgumentParser(allow_abbrev=False)

        parser.add_argument('-u', '--account',    help='Repository account',    default='%SRCSRV_USERNAME%')
        parser.add_argument('-t', '--project-id', help='Repository project ID', required=True)
        parser.add_argument('-i', '--api',        help='REST API version',      default='v4')
        parser.add_argument('-j', '--sudo',       help='REST API sudo user')

        super().__init__(parser=parser, args=args, unparsed_args=unparsed_args)

    @staticmethod
    def json(api_ver, project_id, encoded_file_path):
        '''
        Routing for mocking gitlab REST API first call
        https://docs.gitlab.com/ee/api/repository_files.html#get-file-from-repository
        '''
        print(flask.request.headers)
        print(f'{flask.request.host_url}: {api_ver}/{project_id}/{encoded_file_path}')

        ref = flask.request.args.get('ref')
        with utils.GitGuard(repo=Gitlab.repo, commit=ref) as gg:
            blob_id = gg.repo.git.hash_object(encoded_file_path)
            commit_id = gg.repo.head.object.hexsha

        content = {
            # This is just a subset of the attributes of a real API call
            'file_path': encoded_file_path,
            'ref': ref,
            'blob_id': blob_id,
            'commit_id': commit_id,
        }
        return flask.jsonify(content)

    @staticmethod
    def raw(api_ver, project_id, blob_id):
        '''
        Routing for mocking gitlab REST API second call
        https://docs.gitlab.com/ee/api/repository_files.html#get-raw-file-from-repository
        '''
        print(flask.request.headers)
        print(f'{flask.request.host_url}: {api_ver}/{project_id}/{blob_id}')

        # https://git-scm.com/docs/git-cat-file
        return Gitlab.repo.git.cat_file(['blob', blob_id])

    @classmethod
    def initialize(cls, app):
        '''
        Initialize before mocking Gitlab REST API
        '''
        # In order for the overall package not to have dependencies which are
        # only needed for testing, importing is done during initialization
        global flask
        import git
        import flask
        app.route('/api/<api_ver>/projects/<int:project_id>/repository/files/<path:encoded_file_path>',
                    subdomain='gitlab', methods=['GET',])(cls.json)

        app.route('/api/<api_ver>/projects/<project_id>/repository/blobs/<blob_id>/raw',
                subdomain='gitlab', methods=['GET',])(cls.raw)
        cls.app = app
        cls.working_dir = os.path.join(app.instance_path, 'test', 'repos', 'gitlab')
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
                    '--api':        self.args.api,
                    '--account':    self.args.account,
                    '--project-id': self.args.project_id,
                    '--sudo':       self.args.sudo,
                    '--auth':       auth,
                }
            )

    def header(self, stream) -> bool:
        '''
        Write SRCSRV.ini header

        Parameters:
            stream - SRCSRV.ini stream to write to
        '''
        content = rf'''
SRCSRVCMD={self.args.python} -c "import srcsrv;srcsrv.main([%gl_plugin%,%gl_uri%,%gl_api%,%gl_project%,%gl_account%,%gl_sudo%,%gl_commit%,%gl_verify%,r'-c=%SRCSRVTRG%']).fetch('%var2%','%var3%','%var4%')"
GL_BASE={self.args.build_base}
GL_PLUGIN='-$=srcsrv.plugins.Gitlab'
GL_URI='-@={self.args.uri}'
GL_COMMIT='-#={self.args.commit}'
GL_VERIFY='-v={self.args.verify}'
GL_ACCOUNT='-u={self.args.account}'
GL_PROJECT='-t={self.args.project_id}'
GL_SUDO='-j={self.args.sudo}'
GL_API='-i={self.args.api}'
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
        return super(Gitlab, self).entry(stream=stream,
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
        }

        auth = utils.get_authorization(auth_var=self.AUTH, headers=headers)

        #
        # Codebase requires 2 steps for retrieval. First get the object of the specific
        # commit. Then get the object's content.
        #
        encoded_path = requests.utils.quote(f'{file_path[1:]}{file_name}', safe='')
        # compose REST API call for file information
        # https://docs.gitlab.com/ee/api/repository_files.html#get-file-from-repository
        params = { 'ref': self.args.commit }
        rest_api_call = f'https://{self.args.uri}/api/{self.args.api}/projects/'\
                        f'{self.args.project_id}/repository/'\
                        f'files/{encoded_path}'

        # fetch the JSON response from the repo describing the BLOB
        response = requests.get(rest_api_call,
                                headers=headers,
                                auth=auth,
                                params=params,
                                verify=self.args.verify)
        if response.status_code != 200:
            logging.error(f'REST API call: {rest_api_call}: error {response.status_code}: {response.content}')
            sys.exit(-1)

        # compose REST API call for file content
        # https://docs.gitlab.com/ee/api/repository_files.html#get-raw-file-from-repository
        rest_api_call = f'https://{self.args.uri}/api/{self.args.api}/projects/'\
                        f'{self.args.project_id}/repository/'\
                        f'blobs/{response.json()["blob_id"]}/raw'

        # fetch the file content from the repo
        response = requests.get(rest_api_call,
                                headers=headers,
                                auth=auth,
                                params=params,
                                verify=self.args.verify)
        return super(Gitlab, self).fetch(file_path=file_path,
                                         file_name=file_name,
                                         file_pdb_hash=file_pdb_hash,
                                         response=response,
                                         rest_api_call=rest_api_call,
                                         file_description=self.args.project_id)


__all__ = ['Gitlab']
