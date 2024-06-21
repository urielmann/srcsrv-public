'''
    Bitbucket plugin (work in progress)
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
import logging
import requests
import argparse
# Source index modules
from . import plugin
from .. import utils


class Bitbucket(plugin.Plugin):
    '''
    Bitbucket processing
    '''

    AUTH = 'SRCSRV_BITBUCKET_AUTH'

    class ValidateAPIVersion(argparse.Action):
        '''
        Validate and store 'REST API version'
        '''
        def __init__(self, option_strings, dest, nargs=None, **kwargs):
            super(Bitbucket.ValidateAPIVersion, self).__init__(option_strings, dest, **kwargs)

        def __call__(self, parser, namespace, value, option_string=None):
            try:
                if not value:
                    raise ValueError
                float(value)
            except ValueError:
                # default is REST API version 2.0
                value = '2.0'
            setattr(namespace, self.dest, value)


    def __init__(self, args=None, unparsed_args: argparse.Namespace=None):
        '''
        Bitbucket plugin constructor

        Params:
        args - All currently parsed arguments
        unparsed_args - Remaining arguments to parse
        '''

        # Add plugin specific arguments
        parser = argparse.ArgumentParser(allow_abbrev=False)

        parser.add_argument('-i', '--api',         help='REST API version',
                                                   action=Bitbucket.ValidateAPIVersion, default='2.0')
        parser.add_argument('-t', '--project-key', help='Project key name',     required=True)
        parser.add_argument('-r', '--repo-slug',   help='Repository slug name', required=True)

        super().__init__(parser=parser, args=args, unparsed_args=unparsed_args)

    @staticmethod
    def routes_latest(api_version,
                      project_key,
                      repo_slug,
                      commit,
                      file_path,
                      file_name):
        '''
        Routing for bitbucket REST API current version
        https://developer.atlassian.com/cloud/bitbucket/rest/api-group-source/#raw-file-contents
        '''
        repo_path = f'{file_path}/{file_name}'
        logging.info(flask.request.headers)
        logging.info(f'{flask.request.url}/{api_version}/'\
                     f'{project_key}/{repo_slug}/{commit}/{repo_path}')

        with utils.GitGuard(Bitbucket.repo, commit=commit) as gg:
            blob_id = gg.repo.git.hash_object(repo_path)
            # https://git-scm.com/docs/git-cat-file
            return gg.repo.git.cat_file(['blob', blob_id])

    @staticmethod
    def routes_1_0(api_version,
                   project_key,
                   repo_slug,
                   file_path,
                   file_name):
        '''
        Routing for bitbucket REST API version 1.0
        https://docs.atlassian.com/bitbucket-server/rest/5.16.0/bitbucket-rest.html#idm8297432560
        '''
        commit = flask.request.args.get('at')
        repo_path = f'{file_path}/{file_name}'
        logging.info(flask.request.headers)
        logging.info(f'{flask.request.url}/{api_version}/'\
                     f'{project_key}/{repo_slug}/{repo_path}?'\
                     f'{commit}')

        with utils.GitGuard(Bitbucket.repo, commit=commit) as gg:
            blob_id = gg.repo.git.hash_object(repo_path)
            # https://git-scm.com/docs/git-cat-file
            return gg.repo.git.cat_file(['blob', blob_id])

    @classmethod
    def initialize(cls, app):
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
        app.route('/rest/api/<float:api_version>/projects/<project_key>/repos/<repo_slug>/raw/<path:file_path>/<file_name>',
                  subdomain='bitbucket', methods=['GET',])(Bitbucket.routes_1_0)
        app.route('/<float:api_version>/repositories/<project_key>/<repo_slug>/src/<commit>/<path:file_path>/<file_name>',
                  subdomain='api.bitbucket', methods=['GET',])(Bitbucket.routes_latest)
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
                    '--api':         self.args.api,
                    '--project-key': self.args.project_key,
                    '--repo-slug':   self.args.repo_slug,
                    '--auth':        auth,
                }
            )

    def header(self, stream) -> bool:
        '''
        Write SRCSRV.ini header

        Parameters:
            stream - SRCSRV.ini stream to write to
        '''
        content = rf'''
SRCSRVCMD={self.args.python} -c "import srcsrv;srcsrv.main([%bb_plugin%,%bb_uri%,%bb_api%,%bb_project%,%bb_repo_slug%,%bb_commit%,%bb_verify%,r'-c=%SRCSRVTRG%']).fetch('%var2%','%var3%','%var4%')"
BB_BASE={self.args.build_base}
BB_PLUGIN='-$=srcsrv.plugins.Bitbucket'
BB_URI='-@={self.args.uri}'
BB_COMMIT='-#={self.args.commit}'
BB_VERIFY='-v={self.args.verify}'
BB_API='-i={self.args.api}'
BB_PROJECT='-t={self.args.project_key}'
BB_REPO_SLUG='-r={self.args.repo_slug}'
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
        return super(Bitbucket, self).entry(stream=stream,
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
        # Content type is derived from the repo file type
        # See: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-source/#raw-file-contents
        headers = {}

        auth = utils.get_authorization(auth_var=self.AUTH, headers=headers)

        # compose REST API call
        if self.args.api == '1.0':
            params = { 'at': self.args.commit }
            rest_api_call = f'https://{self.args.uri}/rest/api/1.0/'\
                            f'projects/{self.args.project_key}/'\
                            f'repos/{self.args.repo_slug}/'\
                            f'raw{file_path}'\
                            f'{file_name}'
        else:
            params = None
            rest_api_call = f'https://api.{self.args.uri}/{self.args.api}/'\
                            f'repositories/{self.args.project_key}/'\
                            f'{self.args.repo_slug}/src/{self.args.commit}'\
                            f'{file_path}{file_name}'

        # fetch the source from the repo
        response = requests.get(rest_api_call,
                                headers=headers,
                                auth=auth,
                                params=params,
                                verify=self.args.verify)
        return super(Bitbucket, self).fetch(file_path=file_path,
                                            file_name=file_name,
                                            file_pdb_hash=file_pdb_hash,
                                            response=response,
                                            rest_api_call=rest_api_call,
                                            file_description=f'{self.args.project_key}/'\
                                                             f'{self.args.repo_slug}')


__all__ = ['Bitbucket']
