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
