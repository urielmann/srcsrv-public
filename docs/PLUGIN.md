# Plugins
## Table of Content
- [Plugins](#plugins)
  - [Table of Content](#table-of-content)
- [Adding Custom Plugin](#adding-custom-plugin)
    - [General](#general)
  - [Methods](#methods)

# Adding Custom Plugin
This package includes a few plugins for some popular repositories. It could also serve as a platform for creating your own plugin, if your current SCM is not supported, or you need any additional processing. I tried to make it as simple and easy as possible to aggregate your needs into this code. Should you try and succeed in adding functionality not yet supported by the current package. Please consider contributing your effort to enhance this project and benefit others.  
Here are some guidelines on how to do it:
### General
When the plugin methods are invoked, the class instance data member **self.args** is a [**Namespace**](https://docs.python.org/3/library/argparse.html#argparse.Namespace) of [**argparse** module](https://docs.python.org/3/library/argparse.html#module-argparse) pre-populated with the options passed to the package when it was invoked. The most notable options are:
| Option              | Namespace member         | Description                                     |  Action(s)    |
|---------------------|--------------------------|-------------------------------------------------|---------------|
| --build-base        | **self.args.build_base** | Base path to the source files being indexed     | index         |
| --plugin            | **self.args.plugin**     | Fully qualified name of the plugin class        | index / fetch |
| --action            | **self.args.action**     | Action being preformed (1 - index, 2 - fetch)   | index / fetch |
| --commit            | **self.args.commit**     | Commit hash or tag                              | index / fetch |
| --uri               | **self.args.uri**        | URI of the repo server                          | index / fetch |
| --cache             | **self.args.cache**      | Path to cache directory                         | index / fetch |
| --verify            | **self.args.verify**     | Should SSH verification being done              | index / fetch |
The Namespace will also contain plugin specific options. See \_\_init__ method for more details.

Plugins are derived from the abstract base class of *srcsrv.plugin*. It needs to implement a few basic methods
https://github.com/urielmann/srcsrv/blob/725e84a5ed5fbf2b127128b41208116a5fce2804/srcsrv/plugins/plugin.py#L25-L98


## Methods
1. **\_\_init__** method - The base implementation just save the **args** passed in. If your plugin require some additional options it needs to parse them first. Typically, these will be the login info values. One of the values needed is the environment variable containing the authorization.
```python
    def __init__(self, args=None, unparsed_args: argparse.Namespace=None):
        # Add plugin specific arguments
        parser = argparse.ArgumentParser(allow_abbrev=False)

        parser.add_argument('-t', '--account', help='Repository owner', required=True)
        parser.add_argument('-r', '--repo',    help='Repository name', required=True)
        parser.add_argument('-z', '--auth',    help='REST API authorization information',
                                               default='SRCSRV_GITHUB_AUTH')

        logging.info(unparsed_args)
        # Parse remaining  unrecognized args
        namespace = parser.parse_args(unparsed_args)
        # Complete the initialization by passing values to base class implementation
        super().__init__(args, namespace)
```
2. *header* method - Write to **srcsrv** stream the values needed for invoking the **SRCSRVCMD** script
```python
    def header(self, stream) -> bool:
        '''
        Write SRCSRV.ini header

        Parameters:
            stream - SRCSRV.ini stream to write to
        '''
        content = rf'''
SRCSRVTRG={self.args.cache}/%var4%/%var3%
SRCSRVCMD={self.args.python} -c "import srcsrv;srcsrv.main([%gh_plugin%,%gh_uri%,%gh_acct%,%gh_repo%,%gh_commit%,%gh_verify%]).fetch('%var2%','%var3%','%var4%')"
GH_BASE={self.args.build_base}
GH_PLUGIN='-u=srcsrv.plugins.Github'
GH_URI='-@={self.args.uri}'
GH_ACCT='-t={self.args.account}'
GH_REPO='-r={self.args.repo}'
GH_CACHE='-c={self.args.cache}'
GH_COMMIT='-#={self.args.commit}'
GH_VERIFY='-v={self.args.verify}'
'''
        logging.info(content)
        stream.write(content)
        return True
```
During development use **--dry-run** and **--keep** options to just save temporary files produced by the indexer to troubleshoot issues. It will save the need to rebuild the **.PDB** file over and over during experimentation.