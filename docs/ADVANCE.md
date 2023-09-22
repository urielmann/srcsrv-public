<!--
 ADVANCE.md - Advance topics

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
# Advance Topics
## Table of Content
- [Advance Topics](#advance-topics)
  - [Table of Content](#table-of-content)
- [Source Indexing Primer](#source-indexing-primer)
- [Troubleshooting](#troubleshooting)
  - [Debugging Tools for Windows srcsrv utilities](#debugging-tools-for-windows-srcsrv-utilities)
  - [Debuggers](#debuggers)
  - [SrcTool](#srctool)
  - [PDBStr](#pdbstr)
  - [Logging](#logging)
  - [Breakpoint](#breakpoint)

# Source Indexing Primer

Source indexing operates by embedding special stream into **.PDB** files. Program Database (.**PDB**) is a general purpose structured storage containing various metadata regarding an executable being debugged. The storage is composed of several "streams", each in it's own distinguished format. Some of the streams allow the debugger to match specific offsets in the executable with the program's source code line which generated its machine's instructions. This enables the debugger to highlight the correct source line as you trace the execution in the debugger. The source file name in the **.PDB** is full path to the source at the time the programs was compiled. If the program being debugged is on the same machine where the compilation took place, the debugger can open the source by using the **.PDB** embedded path. However, once the symbols are moved to a different machine, this link is broken.  
Another optional streams in this collection is named *srcsrv*. The stream is a mapping between the source file path in the **.PDB** and the repository where source files are being safeguarded. For obvious reasons this mapping must contain a way to identify the exact revision of the source file which existed at compilation time. This mapping is used by the debugger to first retrieve and then load matching source from your SCM. This retrieval is done by a single line script. The script is executed by the source server module (DLL).  
Since different SCM systems are accessed differently, the *srcsrv* stream contains command to retrieve a specified revision of a source file from a remote repository where it is stored.  

The *srcsrv* stream is relatively simple plain text script composed of three main parts:
1. General metadata variables for the debugger (**SRCSRV: ini**)
2. The second part of the script (**SRCSRV: variables**), are various variables to be used to compose the command retrieving the source code. The most important of these variables are **SRCSRVCMD** - which is the actual command line to invoke - and, **SRCSRVTRG** - which designate the location where the source is cached by the debugger. When the debugger fetches the source code form the repository it simply executes **SRCSRVCMD**. Next it loads the file from **SRCSRVTRG** to trace debugee's execution.  
Each variable is composed of literal parts and placeholders to be substituted by the values of other variables. These placeholders are in the form of a *%var_name%*. The substitution values may come form:  
a) [SRCSRV.ini file](https://docs.microsoft.com/en-us/windows-hardware/drivers/debugger/the-srcsrv-ini-file) variables. This file can override some of the embedded stream's variables. This is needed sometime when the code retrieval has changed since the initial indexing was done (e.g., the repository was moved to different type of SCM or a different server)   
b) The *srcsrv* stream variables embedded in the **.PDB**.  
3. The third (**SRCSRV: source files**), is a table which maps the source files paths embedded in the **.PDB** to the repository path. Each source file appears on a single line starting with the path passed to the compiler at the time the **.PDB** was built (table's "key"). The remainder of the line are various parts of the repository path separated by asterisks and the source file's MD5 or SHA256 digest. In the *srcsrv* stream script these segments appear as **VAR1**, **VAR2**,...**VARn** according to their position on the line.  
The default **srcsrv.ini** file resides in a subdirectory named **srcsrv** of the *Debugging Tools for Windows* installation directory. That path can be modified by setting *SRCSRV_INI_FILE* environment variable.   

Here's an example *srcsrv* stream:  

```text
SRCSRV: ini ------------------------------------------------
VERSION=2
VERCTRL=
SRCSRV: variables ------------------------------------------
SRCSRVTRG=C:/Users/umann/srcsrv/%var4%/%var3%
SRCSRVCMD=py.exe -c "import srcsrv;srcsrv.main([%bb_plugin%,%bb_uri%,%bb_api%,%bb_project%,%bb_repo_slug%,%bb_commit%,%bb_verify%]).fetch('%var2%','%var3%','%var4%')"
BB_BASE=c:\srcsrv\test\repos\bitbucket\
BB_PLUGIN='--plugin=srcsrv.plugins.Bitbucket'
BB_URI='--uri=bitbucket.com'
BB_API='--api=2.0'
BB_PROJECT='--project-key=urimann'
BB_REPO_SLUG='--repo-slug=srcsrv'
BB_COMMIT='--commit=V1'
BB_VERIFY='--verify=None'
SRCSRV: source files ---------------------------------------
c:\Play\new-srcsrv\test\repos\bitbucket\test\src\test.cpp*/test/src/*test.cpp*15C843B956C64EAD5A67C46FB9F64D96*1ab6cdd48d27232227756fba27490073d1c94b3d
c:\Play\new-srcsrv\test\repos\bitbucket\test\src\inc\test.h*/test/src/inc/*test.h*54E04C0C4D76FACADCB2CF6E220B46CE*05ba7838f6a0a6cda92f7e1c7d69ad817cc8c917
SRCSRV: end ------------------------------------------------
```

# Troubleshooting

It was said before that great software just works correctly. While this is true in a perfect world, there are times that this ideal is not met. The most challenging part is typically initial setup. For this purpose this package provides various ways of figuring what is happing during source indexing and source retrieval. Occasionally, even after the initial setup, there's also a need to investigate why the package works in some environments but not in others.  
The *srvsrv* package has facilities to aid you during the investigation. One is by enabling logging. The other is by triggering a debugger breakpoint and stepping through the python code.  
Both actions can be accomplished by modifying the script invoked by the debugger. This can be done in one of two ways
1. By calling the script directly
2. Forcing the debugger to call a modified script
3. Forcing *srctool.exe* to call a modified script.  
## Debugging Tools for Windows srcsrv utilities
In both cases you'll need to use [*srctool.exe*](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/the-srctool-utility) and [*pdbstr.exe*](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/the-pdbstr-tool) utilities. These executables can be found in the **srcsrv** directory mentioned above.  
## Debuggers
Each of the debuggers can be configured to show the SrcSrv scrip.  To see the script you need to start the debugger with -n for the command line debuggers (windbg.exe, windbgx.exe, kd.exe, cdb.exe, or ntsd.exe). The **!sym noisy** will do the same thing when you're in the debugging session.  
For Visual Studio IDE select from the menu **Tools > Options... > Debugging** and check **Print source sever diagnostic message to the Output window**![Debuggin](./assets/VS_Options+.png)
## SrcTool
This utility can be used to view the script command as well to test extract source files indexed in the **.PDB**. This is usually much easier than doing it using a debugger. The most useful command line options are.  
1. **-n** - Show the extraction stript  
2. **-x** - Extract one or more files  
3. **-l:<file_path>** or **-lf:<file_name>** - Which filter which file or files will be extracted  
Use the **-?** on the command line to see all options.  
For example:
```text
C:\>srctool.exe -lf:test.h -n test.pdb
[S:\srcsrv\test\repos\github\test\src\inc\test.h] cmd: py.exe -c "import srcsrv;srcsrv.main(['--plugin=srcsrv.plugins.Github','--uri=github.com','--account=urimann','--repo=srcsrv','--commit=V1','--verify=None']).fetch('/test/src/inc/','test.h','B6749E8AA08549786DFD89C8A5BB6F52')"
test.pdb: 1 source file was found.
```
## PDBStr
The *pdbstr.exe* utility allow to extract the srcsrv stream from the symbols file. The general format is:  
**pdbstr.exe -r -p:<path2pdb> -s:srcsrv -i:<path2output>.ini**. Once you invoke the command you can look at the output file to see the variable information you need to change to enable logging or trigger debugger breakpoint in so you can step through the extraction script.  
## Logging
By default logging is disabled. To enable it you'll need to add **--log=<log_file>** option. To simply send logging to *stdout* use dash (**-**) as the log name. This will send logging to the debugger output pane. Otherwise, provide a path to the log file.  
Now you can modify the command from the example above to add logging.  
```text
C:\>py.exe -c "import srcsrv;srcsrv.main(['....','--log=-']).fetch('/test/src/inc/','test.h','B6749E8AA08549786DFD89C8A5BB6F52')"
2023-08-20 13:39:43,431 - root - INFO - ['--account=urimann', '--repo=srcsrv']
2023-08-20 13:39:43,815 - root - INFO - REST API call: https://api.github.com/repos/urimann/srcsrv/contents/test/src/inc/test.h
2023-08-20 13:39:43,834 - root - INFO - adding to inventory test.h: github.com/urimann/srcsrv/test/src/inc/test.h:V1

```
## Breakpoint
To trigger a breakpoint and allow you to attach a python debugger add **--debug** option. Before you can do it you need to be set up for python debugging. The best way to debug python scripts is by using [VSCode](https://code.visualstudio.com/download) with [python extension package](https://marketplace.visualstudio.com/items?itemName=ms-python.python). After installation, add the following to your **launch.json** file:
```json
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Remote Attach",
            "type": "python",
            "request": "attach",
            "port": 5678,
            "host": "localhost",
            "justMyCode": false,
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "."
                }
            ]
        },
        //...more...
    ]
}
``` 
Same as the logging example above, add the **--debug** option to your script. When the script is executed you'll see the message: **Waiting for debugger to attach**. One you attach the debugger you can step through the code or add more breakpoints.  
```text
C:\>py.exe -c "import srcsrv;srcsrv.main(['....','--debug']).fetch('/test/src/inc/','test.h','B6749E8AA08549786DFD89C8A5BB6F52')"
Waiting for debugger to attach
```
![Dbugging](assets/debugging.gif)
At that point you can attach and step through the package code as sown in the clip above.
