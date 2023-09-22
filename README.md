<!--
 README.md - General purpose information

 Copyright (C) 2023 Uri Mann (abba.mann@gmail.com)

 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
-->
# Source Indexing  

## Table of Content

- [Source Indexing](#source-indexing)
  - [Table of Content](#table-of-content)
  - [Disclaimer](#disclaimer)
  - [Package Description](#package-description)
  - [Usage](#usage)
    - [Common options](#common-options)
    - [Indexing operation](#indexing-operation)
    - [Source fetching operation](#source-fetching-operation)
    - [Common diagnostic options](#common-diagnostic-options)
    - [Build diagnostic options](#build-diagnostic-options)
- [Plugins](#plugins)
  - [Github options](#github-options)
  - [Github environment](#github-environment)
  - [Bitbucket options](#bitbucket-options)
  - [Bitbucket environment](#bitbucket-environment)
  - [Gitlab options](#gitlab-options)
  - [Gitlab environment](#gitlab-environment)
  - [Codebase options](#codebase-options)
  - [Codebase environment](#codebase-environment)
  - [Options file](#options-file)
- [External Links](#external-links)

## Disclaimer

The author of this package does not warrant that the functionality contained in the package will meet your requirements or that the operation of the package will be uninterrupted or error-free.  Note: In no event will the author be liable to you for any damages, including any corruption of binaries or PDBs, lost profit, lost savings, lost patience or other incidental or consequential damage.  

With that part out of the way, my goal is to make something that is useful. If you'd like to request additional features, report bugs or provide any other feedback, feel free to reach me.  
[Uri Mann](mailto:abba.mann@gmail.com)  

## Package Description

This package provides two distinct operations needed for source indexing functionality.  
1. Python script to add source indexing information to **.PDB** files. The added information allows the debugger to automatically pull the version of the source code used at build time from a repository. The python script can be invoked on each **.PDB** file after the link phase of the build is completed. Alternatively, the script can receive a list of one or more directories where the **.PDBs** are placed at the end of the build. Internally, the script simply scans each directory recursively and invoke itself on each file with **.pdb** extension.
2. Python script to fetch the source code files from the remote repository and cache them for use by the debugger. That script is invoked by the debugger when it detects that the source code for next line is not cached on the debugging host machine.

## Usage
Note that some of the command line options are common to both index and fetch operation while others are operation specific. Additionally, each plugin has specific additional operational options as well. Some options have default values which will be used if the option is omitted.  
The option and the value may be separated by a space or equal sign (=) (e.g., both --log output.log and --log=output.log are the same). 

### Common options

>**-$**, **--plugin** - Plugin class. default is *srcsrv.plugins.Github*. Plugin classes available in current release: *srcsrv.plugins.Github*, *srcsrv.plugins.Bitbucket*, *srcsrv.plugins.Codebase* or *srcsrv.plugins.Gitlab*.  
>**-@**, **--uri** - Git repository server URI. default github.com  
>**-#**, **--commit** - Build commit hash or label. This option can be omitted. If not provided the package is assuming the current directory is the repository and the uses current HEAD hash.  
>**-!**, **--action** - Plugin action with choice between *index* or *fetch* (default *fetch*).  

### Indexing operation
>**-p**, **--pdbs** - List of paths to **.PDB** files to process or directories to scan for symbol files *(e.g.: -p c:\path\file1.pdb c:\path\file2.pdb d:\symdir1  d:\symdir2)*.  The script will recurs to each sub-directory in the specified list. The path is assumed to be fully-qualified or relative to current directory.  
>**-b**, **--build-base** - Root of the build directory. This path correspond with top of the repository branch being built (i.e., where **.git** is placed).  
>**-x**, **--extensions** - Semicolon separated list of source extensions (default:cpp;hpp;c;h).  
>**-s**, **--srcsrv** - Path to SDK or DDK source indexing directory. Default path is **C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\srcsrv** (Windows 10 **DTfW** or newer required). Download and install [Debugging Tools for Windows](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/debugger-download-tools).  

### Source fetching operation
>**-c**, **--cache** - Source files cache directory. By default this is user's home (*%USERPROFILE%*) directory. The source files retrieved from the repository will be stored in a subdirectory name **srcsrv**.  
>**-v**, **--verify** - Should the script do SSL certificate validation of the remote repository. Possible options are *True*, *False*, *0*, *1* or *None* (default: *None*).  
>**-e**, **--python** - Path of python executable used to for running the script. The default is **py.exe** (Python launcher).  

### Common diagnostic options
>**-l**, **--log** - Path to log file. By default logging is not enabled. The dash (-) will send logging to *stdout*.  
>**-d**, **--debug** - Allows attaching remote debugger to the script execution. This option is using [debugpy](https://github.com/microsoft/debugpy) local connection on port 5678.  

### Build diagnostic options
>**-k**, **--keep** - Keep (don't delete after processing) the **.PDB** stream input file. With this option specified the file is kept in the same directory as the **.PDB**. The file will have the same base name as the **.PDB** file with the extension **.ini** (e.g., *prog.pdb* will have corresponding *prog.ini*).  
>**-n**, **--dry-run** - The script is run without modifying the **.PDB**. While it is possible to index the same symbols file multiple times it is not recommended. Each operation adds another **srcsrv** stream instead of overwriting the existing one. This option should be used with with **--keep** option when setting for diagnosing source indexing for the first time.  
<!-- @TODO:
>**-m**, **-summary** - Produce indexing summary file path. The file contains to options and stats for the indexing operation.  
>**-q**, **--level** - Summary level (minimal, normal, detailed or verbose).  
-->

# Plugins
Each plugin has unique name of an environment variable containing the authentication used to connect to the remote repository. The value stored in the environment variable will be evaluated as python language expression. It is expected to be in one of three types. See more information in the plugins section.  
>1. Dictionary (*dict*) entry which is interpreted as HTTPS Authorization header (e.g., *{'Authorization':'Bearer &lt;token&gt;'}*).  
>2. Tuple (*tuple*) value which in interpreted as HTTPS basic authentication (e.g., *('&lt;account&gt;','&lt;password&gt;')*).  
>3. The value is missing or *None* to indicate no authentication is required by the remote repository.  
## Github options
>**-u**, **--account** - User's account.  
>**-r**, **--repo** - Github repository name.  
## Github environment
>**SRCSRV_GITHUB_AUTH** - User [token](https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line) This is expected to be the string in the format of *{'Authorization':'Token &lt;token&gt;'}*. The value is evaluated as a python language expression.  

## Bitbucket options
>**-i**, **--api** - Version of [Bitbucket REST API](https://docs.atlassian.com/bitbucket-server/rest/latest/bitbucket-rest.html) used. The default is *2.0*.  
>**-t**, **--project-key** - Project key name.  
>**-r**, **--repo-slug** - Repository slug name.  
## Bitbucket environment
>**SRCSRV_BITBUCKET_AUTH** - User [token](https://developer.atlassian.com/cloud/bitbucket/rest/intro/#authentication_old). This is expected to be the string in the format of *{'Authorization':'Bearer &lt;token&gt;'}*. The value is evaluated as a python language expression.  

## Gitlab options
>**-u**, **--account** - User's account.  
>**-t**, **--project-id** - Project id value.  
<!--
@TODO:
>**-S**, **--sudo** - Gitlab repository sudo account name.  
-->
>**-i**, **--api** - Version of [Gitlab REST API](https://docs.gitlab.com/ee/api/rest/) used. The default is *v4*.
## Gitlab environment
>**SRCSRV_GITLAB_AUTH** - *Token* used for authorization This is expected to be the string in the format of *{'Authorization':'Bearer &lt;token&gt;'}*. The value is evaluated as a python language expression.  
. It may be one of three token types.  
>1. [Personal access tokens](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html).  
>2. [Project access tokens](https://docs.gitlab.com/ee/user/project/settings/project_access_tokens.html)
>3. [Group access tokens](https://docs.gitlab.com/ee/user/group/settings/group_access_tokens.html)
  

## Codebase options
>**-u**, **--account** - User's account.  
>**-i**, **--domain** - Codebase repository domain.  
>**-t**, **--proj-permalink** - Project perma link.  
>**-r**, **--repo-permalink** - Repository perma link.  
>**-j**, **--api** - REST API version (default is *api3*).  
## Codebase environment
>**SRCSRV_CODEBASE_AUTH** - [Basic authentication used for authorization](https://support.codebasehq.com/kb). This is expected to be the string in the format of *('&lt;domain&gt;/&lt;account&gt;':'&lt;token&gt;')*. The value is evaluated as a python language expression.  

## Options file
For indexing operation the script can also be invoked with a response file. Using **@path\resp_file_name**. The file can contain any of the above parameters. Response file and command line parameters can be combined. Example:

```
--action index
--build-base D:\dev\myproject
--uri bitbucket.com
--pdbs test.pdb
--api 1.0
--project-key myproj
--repo-slug testing
--commit release-1.0.0
--log ..\srcsrv.log
--plugin srcsrv.plugins.Bitbucket
```
Similar to the command line the option and argument may be separated by space, new line, or equal sign.  
# External Links

[Srcsrv.doc](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=3&ved=2ahUKEwjO_sL72NHlAhVYnp4KHcdmCdgQFjACegQIAxAC&url=https%3A%2F%2Fcrashopensource.files.wordpress.com%2F2007%2F10%2Fsrcsrv.doc&usg=AOvVaw0ONZV3AtYTB1S8sgPqhTsU)  
[The SrcTool Utility](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/the-srctool-utility)  
[Source Indexing is Underused Awesomeness](https://randomascii.wordpress.com/2011/11/11/source-indexing-is-underused-awesomeness/)  
[Debugging with source indexed **.PDB**](docs/SETUP.md)  
[Advance topics **.PDB**](docs/ADVANCE.md)  
