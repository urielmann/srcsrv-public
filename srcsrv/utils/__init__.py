'''
    Utilities package
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

import os
import git
import enum
import logging

class GitGuard:
    '''
    Fixture to switch repository to specific commit and switch back
    '''
    def __init__(self, repo:git.Repo, commit:str=None):
        super(GitGuard, self).__init__()
        self.commit = commit
        self.repo = repo

    def __enter__(self):
        '''
        Checkout commit
        '''
        self.repo.git.checkout(self.commit)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        '''
        Restore to previous commit.
        '''
        self.repo.git.switch('-')

class ValidateAction(enum.IntEnum):
    '''
    Action type enumeration
    '''
    INDEX = 1
    FETCH = 2

    # magic methods for argparse compatibility

    def __str__(self):
        return self.name.lower()

    def __repr__(self):
        return str(self)

    @staticmethod
    def argparse(s):
        try:
            return ValidateAction[s.upper()]
        except KeyError:
            error = f'Invalid action {s}'
            logging.exception(error, stack_info=True)
            return s

def get_authorization(auth_var:str, headers:dict):
    '''
    Evaluate REST API authentication

    This method gets the connection authorization needed to connect to REST
    API server. The authentication is will fall into one of three options:
    1. No authorization required (None)
    2. HTTPS basic authorization tuple (e.g., ('<user_acct>', '<password>'))
    3. HTTPS header dictionary entry (e.g., {'Authorization': 'Token <user_token>'})
    The value will be either contained in an environment variable or it will be directly
    specified as the 'auth' value.

    Params:
        auth_var - Name of environment variable containing authorization expression. The
                   expression could be one of three types
                   1. Environment variable not defined or defined as 'None'. No authorization
                      is require (no security)
                   2. Tuple expression containing user account and password for 'basic'
                      authorization.
                   3. Dictionary expression in the form of authorization header
        header - Existing HTTPS headers. Dictionary entries are assumed to be headers
                 and will be added to headers list
    '''
    # Make sure that code can't be injected!
    try:
        # Q: Does the environment contains authorization object
        auth = eval(os.environ[auth_var], {}, {})
    except KeyError as ex:
        logging.warning(f'{auth_var} is not defined')
        # No authorization is required
        return None
    except SyntaxError as ex:
        # Environment variable does not contain valid python expression
        logging.exception(ex, stack_info=True)
        raise

    # Q: Authorize with 'Authorization:' header?
    if type(auth) == dict:
        headers.update(auth)
        return None
    # Q: Authorize with user/password tuple?
    elif auth is not None and type(auth) != tuple:
        error = f'Invalid authorization type {auth}'
        logging.exception(error, stack_info=True)
        raise TypeError(error)

    return auth

__all__ = ['GitGuard', 'ValidateAction', 'get_authorization',]
