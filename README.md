# LLDB SOS Extensions
LLDB python scripts to extend SOS commands for .NET debugging on Linux

## Importing the commands
In LLDB, execute:

```lldb
command script import <path to>/LldbSosExts.py
```

## Commands

- **allclrstacks** - Prints CLR stacks for all the threads in the process
- **rsc** - Runs an SOS command and writes its output to a file (tempsos.txt)
- **gfs** - Gets the first instance of a type from the top of the thread stack
- **dko** - Dumps the simplified contents of a known .NET object
- **etec** - Expands thread execution context of first thread on the stack
- **eoh** - Executes a command on every object address given a method table address
- **dhbg** - Dumps heap by MethodTable reference and GC Generation
- **dhbgr** - Dumps heap by MethodTable reference and GC Generation where the objects have a GC Root

### eoh

```lldb
eoh <mt addr> <cmd>
```

Get the Method Table (mt) address (e.g. like from dumpheap output). The cmd is a single word command to run on each object address. The eoh command runs a `dumpheap -short -mt <mt addr>` and then runs `cmd` on each object address.

## Troubleshooting

If you get something like `NameError: name 'run_one_line' is not defined`, there is an issue with the Python installation. Exit LLDB and try running these commands:

```shell
sudo apt update
sudo apt install python3
sudo apt install python3-lldb
ln -s /usr/lib/llvm-14/lib/python3.10/dist-packages/lldb/* /usr/lib/python3/dist-packages/lldb/
```
