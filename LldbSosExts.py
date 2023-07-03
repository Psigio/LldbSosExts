from __future__ import print_function
import lldb
import argparse
import re
import datetime
import json

TEMP_FILENAME = "tempsos.txt"

def read_from_file():
    with open(TEMP_FILENAME, 'r') as f:
        content = f.readlines()
    return content

def run_sos_cmd(debugger, raw_args, result, internal_dict, echo_to_stdout = True):
    old_file = debugger.GetOutputFile()
    with open(TEMP_FILENAME, 'w') as sos_file:
        debugger.SetOutputFile(sos_file)
        debugger.HandleCommand(raw_args)
        debugger.SetOutputFile(old_file)
    
    content = read_from_file()
    if echo_to_stdout:
        for line in content:
            print(line, end='')
    return content

def get_from_stack(debugger, raw_args, result, internal_dict, echo_to_stdout = True):
    content = run_sos_cmd(debugger, 'dso', result, internal_dict, False)
    re_split = "^([a-f0-9]+)\s([a-f0-9]+)\s(.*)$"
    obj_addr = ''
    if not raw_args:
        match = re.search(re_split, content[len(content) - 1], re.IGNORECASE)
        obj_addr = match.group(2)
    else:
        for line in reversed(content):
            match = re.search(re_split, line, re.IGNORECASE)
            if match.group(3).lower() == raw_args.lower():
                obj_addr = match.group(2)
                break
    
    return run_sos_cmd(debugger, 'dumpobj ' + obj_addr, result, internal_dict, echo_to_stdout)

def get_field_from_dumpobj_content(content, field_name):
    re_field = "^.*\s([a-f0-9]+)\s" + field_name + "$"
    for line in content:
        match = re.search(re_field, line, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def get_field_from_dumpobj(debugger, raw_args, result, internal_dict, echo_to_stdout = True):
    split = raw_args.split(" ")    
    content = run_sos_cmd(debugger, 'dumpobj ' + split[0], result, internal_dict, False)
    field_value = get_field_from_dumpobj_content(content, split[1])
    if echo_to_stdout:
        print(field_value)
    return field_value

def get_keyvalue_dict(debugger, raw_args, result, internal_dict, echo_to_stdout = True):
    content = run_sos_cmd(debugger, 'dumparray -details ' + raw_args, result, internal_dict, False)
    kv_dict = {}
    re_key = "^.*\s+([a-f0-9]*[a-f1-9][a-f0-9]*)\s+key$"
    re_val = "^.*\s+([a-f0-9]*[a-f1-9][a-f0-9]*)\s+value$"
    key_addr = None
    for line in content:
        match = re.match(re_key, line, re.IGNORECASE)
        if match:
            key_addr = match.group(1)
        else:
            match = re.match(re_val, line, re.IGNORECASE)
            if match:
                kv_dict[key_addr] = match.group(1)
    
    if echo_to_stdout:
        print(kv_dict)
    return kv_dict

def get_dumpobj_bool(content):
    bool_val = get_field_from_dumpobj_content(content, 'm_value')
    return bool_val == 1

def get_dumpobj_string(content):
    str_value = ''
    for line in content:
        match = re.match("^String:\s+(\S.*)$", line, re.IGNORECASE)
        if match:
            str_value = match.group(1)
            break
    return '"' + str_value + '"'

def dump_gen_dict(debugger, raw_args, result, internal_dict, echo_to_stdout = True):
    entries_addr = get_field_from_dumpobj(debugger, raw_args + ' _entries', result, internal_dict, False)
    entries_dict = get_keyvalue_dict(debugger, entries_addr, result, internal_dict, False)
    out_dict = {}
    for k in entries_dict:
        key_expanded = dump_known_obj(debugger, k, result, internal_dict, False)
        val_expanded = dump_known_obj(debugger, entries_dict[k], result, internal_dict, False)
        out_dict[key_expanded] = val_expanded
    if echo_to_stdout:
        print(out_dict)
    return out_dict

def dump_known_obj(debugger, raw_args, result, internal_dict, echo_to_stdout = True):
    content = run_sos_cmd(debugger, 'dumpobj ' + raw_args, result, internal_dict, False)
    match = re.match(r"^Name:\s+(\S.*)$", content[0], re.IGNORECASE)
    output = 'Unknown'
    if match:
        typename = match.group(1)
        if typename == 'System.Boolean':
            output = 'bool ' + get_dumpobj_bool(content)
        elif typename == 'System.String':
            output = 'string ' + get_dumpobj_string(content)
        elif typename == 'System.TimeSpan':
            output = 'timespan ' + get_dumpobj_timespan(content)
        elif typename == 'System.DateTime':
            output = 'datetime ' + get_dumpobj_datetime(content)
        elif typename.startswith('System.Collections.Generic.Dictionary`2['):
            output = 'dictionary\n' + json.dump(dump_gen_dict(debugger, raw_args, result, internal_dict, False))
        elif typename == 'Microsoft.Data.ProviderBase.TimeoutTimer':
            output = 'TimeoutTimer expires: ' + get_dumpobj_timeouttimer(content)
        else:
            output = typename
    if echo_to_stdout:
        print(output)
    return output

def expand_thread_exec_ctxt(debugger, raw_args, result, internal_dict):
    content = get_from_stack(debugger, 'System.Threading.Thread', result, internal_dict, False)
    exec_ctxt_addr = get_field_from_dumpobj_content(content, '_executionContext')
    loc_val_addr = get_field_from_dumpobj(debugger, exec_ctxt_addr + ' m_localValues', result, internal_dict, False)
    kv_addr = get_field_from_dumpobj(debugger, loc_val_addr + ' _keyValues', result, internal_dict, False)
    loc_val_dict = get_keyvalue_dict(debugger, kv_addr, result, internal_dict, False)
    for k in loc_val_dict:
        dump_known_obj(debugger, loc_val_dict[k], result, internal_dict)

def allclrstacks(debugger, command, result, internal_dict):
    """Prints CLR stacks for all the threads in the process"""
    numthreads = debugger.GetSelectedTarget().process.num_threads
    for threadnum in range(1, numthreads + 1):
        debugger.HandleCommand('threads ' + str(threadnum))
        debugger.HandleCommand('clrstack ' + command)

def convert_sec_to_date(sec):
    return datetime.datetime.fromtimestamp(sec).strftime("%Y-%m-%d %H:%M:%S.%f")

def read_windows_file_time(filetime):
    sec_since_epoch = (int(filetime) / 10000000) - 11644473600
    return convert_sec_to_date(sec_since_epoch)

def get_dumpobj_timeouttimer(content):
    timer_expire = get_field_from_dumpobj_content(content, '_timerExpire')
    return read_windows_file_time(timer_expire)

def get_dumpobj_timespan(content):
    ticks = get_field_from_dumpobj_content(content, '_ticks')
    if not ticks:
        return '0 ms'
    milliseconds = int(ticks) / 10000
    return str(milliseconds) + ' ms'

def get_dumpobj_methodtable(content):
    for line in content:
        if line.startswith('MethodTable:'):
            return line[line.rindex(' ') + 1]
    return None

def get_dumpobj_datetime(content):
    ticks_with_flags = get_field_from_dumpobj_content(content, '_dateData')
    if not ticks_with_flags:
        return 'unknown'
    # removes flags
    ticks = int(ticks_with_flags) & 0x3FFFFFFFFFFFFFFF
    ticks_since_epoch = ticks - 621355968000000000
    if ticks_since_epoch <= 0:
        return 'min'
    sec_since_epoch = ticks_since_epoch / 10000000
    if sec_since_epoch >= 253402300000:
        return 'max'
    return convert_sec_to_date(sec_since_epoch)

# def get_datetime(debugger, raw_args, result, internal_dict, methodtable_addr = None):
#     if not methodtable_addr:
#         name2ee_content = run_sos_cmd(debugger, 'name2ee System.Private.CoreLib.dll!System.DateTime', result, internal_dict, False)
#         methodtable_addr = get_dumpobj_methodtable(name2ee_content)
    
#     dumpvc_content = run_sos_cmd(debugger, 'dumpvc ' + methodtable_addr + ' ' + raw_args, result, internal_dict, False)
#     datedata = int(get_field_from_dumpobj_content(dumpvc_content, '_dateData'))
    

# name2ee System.Private.CoreLib.dll!System.TimeSpan
# name2ee System.Private.CoreLib.dll!System.DateTime
# name2ee System.Private.CoreLib.dll!System.Threading.Tasks.Task
# dumpheap -mt <mtaddr> -short
# foreach objaddr: tks <objaddr>

def exec_on_heap(debugger, raw_args, result, internal_dict, echo_to_stdout = True):
    split = raw_args.split(" ")
    content = run_sos_cmd(debugger, 'dumpheap -short -mt ' + split[0], result, internal_dict, False)
    for line in content:
        exec_output = ''
        if split[1] == 'dko':
            exec_output = dump_known_obj(debugger, line, result, internal_dict, False)
        else:
            cmd_content = run_sos_cmd(debugger, split[1] + ' ' + line, result, internal_dict, False)
            exec_output = cmd_content[0]
        print(line.rstrip().rjust(20) + ' ' + exec_output.rstrip())

# dumpheap -mt <methodtable_address> -short
# foreach object_address: sos GCWhere <object_address>
# where Generation == generation_number then print
def dumpheap_by_generation(debugger, raw_args, result, internal_dict):
    split = raw_args.split(" ")
    methodtable_address = split[0]
    gc_generation_filter = split[1]
    output = []
    dumpheap_content = run_sos_cmd(debugger, 'dumpheap -short -mt ' + split[0], result, internal_dict, False)
    for dumpheap_line in dumpheap_content:
        # Each line is an object address - call GCWhere on it
        gcwhere_content = run_sos_cmd(debugger, 'sos GCWhere ' + dumpheap_line, result, internal_dict, False)
        # The GCWhere command returns a header that we need to ignore
        gcwhere_line = gchwere_content.pop(0) # Pop the header off
        gcwhere_line = gchwere_content.pop(0) # Pop the content off
        # The 1st item is the address, and the 2nd item is the GC Generation number.  The values are delimited by a variable amount of spaces, so we need to split, filter out the empty strings (None) and then convert back to a List
        filtered_values = list(filter(None, input.split(' ')))
        gc_generation = filtered_values[1]
        if gc_generation == gc_generation_filter:
            output.append(filtered_values[0])
    # We have iterated
    for filtered in output:
        print(filtered)
    print('Done ' + len(output))
        
# And the initialization code to add your commands
def __lldb_init_module(debugger, internal_dict):
    cmd_prefix = 'command script add -f LldbSosExts.'
    debugger.HandleCommand(cmd_prefix + 'run_sos_cmd rsc')
    debugger.HandleCommand(cmd_prefix + 'get_from_stack gfs')
    debugger.HandleCommand(cmd_prefix + 'expand_thread_exec_ctxt etec')
    debugger.HandleCommand(cmd_prefix + 'dump_known_obj dko')
    debugger.HandleCommand(cmd_prefix + 'allclrstacks allclrstacks')
    debugger.HandleCommand(cmd_prefix + 'exec_on_heap eoh')
    debugger.HandleCommand(cmd_prefix + 'dumpheap_by_generation dhbg')
    print('The "rsc,gfs,etec,dko,allclrstacks,eoh,dhbg" python commands have been installed and are ready for use.')
