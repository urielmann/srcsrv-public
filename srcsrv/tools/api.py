'''
Mock REST API
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
import os
import pip
import flask
import logging
import importlib

srvsrv_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..')
srvsrv_dir = os.path.normpath(srvsrv_dir)


#
# @IMPORTANT: Entries must be added to hosts file
# C:\Windows\System32\drivers\etc\hosts
# 127.0.0.1 bitbucket.srcsrv api.bitbucket.srcsrv api3.codebase.srcsrv api.github.srcsrv gitlab.srcsrv
#
# To start: flask.exe --app api.py run
#

app = flask.Flask(__name__,
                  subdomain_matching=True,
                  instance_path=srvsrv_dir)
app.config['SERVER_NAME'] = 'srcsrv:5000'

def load_plugin():
    plugin_name = os.environ['SRCSRV_PLUGIN']
    # Validate plugin class
    try:
        module, klass = plugin_name.rsplit('.', 1)
        mdl = importlib.import_module(module)
        plugin = getattr(mdl, klass)
    except ValueError as err:
        error = f'{plugin_name} does not look like a module path'
        logging.exception(error, stack_info=True)
        raise ImportError(error) from err
    except AttributeError as err:
        error = f'Module {module} does not define a {klass} attribute/class'
        logging.exception(error, stack_info=True)
        raise ImportError(error) from err

    # Instantiate plugin class
    plugin.initialize(app=app)

load_plugin()

def main(debug=False):
    '''
    Main entry point

    Params:
        debug - Attache to debugger
    '''
    if debug:
        try:
            import debugpy
        except ImportError:
            pip.main(['install', '--upgrade', 'debugpy'])
            import debugpy

        try:
            # Flask will restart itself. The debugger will will not be able to bind to the same
            # port. A lock file is opened to detect if this is the first or second instance.
            with open('.lock'):
                debugpy.listen(5680, in_process_debug_adapter=True)
        except FileNotFoundError:
            with open('.lock', 'w'):
                debugpy.listen(5679, in_process_debug_adapter=True)
        print("Waiting for debugger to attach")
        debugpy.wait_for_client()
        debugpy.breakpoint()
        print('Stopped')

    app.run(host='0.0.0.0',
            debug=True,
            ssl_context=('C:/Play/new-srcsrv/test/certs/cert.pem',
                         'C:/Play/new-srcsrv/test/certs/key.pem'))
    if debug:
        os.unlink('.lock')

if __name__ == '__main__':
    main(debug=False)
