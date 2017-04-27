#!/usr/bin/python3

import concurrent.futures
import os
import sys
import multiprocessing
import threading
import traceback

from colors import Colors
from dataparser import eve
from dataparser import mon
from dataparser import exceptions


evecollections = dict()
sysstatcollections = dict()
psstatcollections = dict()
eveparser = eve.EveParser()
sysstatparser = mon.SysStatParser()
psstatparser = mon.PsStatParser()

# The number of concurrent workers equals the number of CPU threads.
NUM_WORKERS = multiprocessing.cpu_count() 


def get_all_logdirs(path, depth=2):
    if depth == 1:
        print('Adding all dirs under "%s".' % path)
        return sorted([path + '/' + i for i in os.listdir(path) if os.path.isdir(path + '/' + i)])
    all_logdirs = []
    for name in os.listdir(path):
        if os.path.isdir(path + '/' + name):
            all_logdirs += get_all_logdirs(path + '/' + name, depth=depth-1)
    return all_logdirs


_collection_lock = threading.Lock()
_task_count_lock = threading.Lock()
task_count = dict()


def get_collection(collections, name, default_class):
    _collection_lock.acquire()
    if name not in collections:
        c = collections[name] = default_class(name)
    else:
        c = collections[name]
    _collection_lock.release()
    return c


def get_collection_name(conf, trace_file, runmode, ninstances, nnics, i, ts):
    return ','.join([conf, trace_file, runmode, ninstances, nnics])


def _parse_csvstat(collections, cls, parser, path, conf, trace_file, runmode, ninstances, nnics, i, ts):
    if os.path.isfile(path):
        thname = threading.current_thread().name
        if thname not in task_count:
            _task_count_lock.acquire()
            task_count[thname] = 1
            _task_count_lock.release()
        else:
            task_count[thname] += 1
        print('\033[93m[%s]\033[0m Start "%s" (%d).' % (thname, path, task_count[thname]))
        name = get_collection_name(conf, trace_file, runmode, ninstances, nnics, i, ts)
        col = get_collection(collections, name, cls)
        try:
            id = col.get_key(conf, trace_file, runmode, ninstances, nnics, i, ts)
            data = parser.parse(path)
            col.add(id, data)
        except exceptions.NoContentException as ex:
            print('Error: ' + str(ex))
        print('\033[92m[%s]\033[0m Done "%s" (%d).' % (thname, path, task_count[thname]))


def parse_sysstat(path, conf, trace_file, runmode, ninstances, nnics, i, ts):
    _parse_csvstat(sysstatcollections, mon.SysStatCollection, sysstatparser,
        path, conf, trace_file, runmode, ninstances, nnics, i, ts)


def parse_psstat(path, conf, trace_file, runmode, ninstances, nnics, i, ts):
    _parse_csvstat(psstatcollections, mon.PsStatCollection, psstatparser,
        path, conf, trace_file, runmode, ninstances, nnics, i, ts)


def parse_eve(path, conf, trace_file, runmode, ninstances, nnics, i, ts):
    _parse_csvstat(evecollections, eve.EveCollection, eveparser,
        path, conf, trace_file, runmode, ninstances, nnics, i, ts)


def execute(all_futures, executor, func, *args):
    print('\033[94m[%s]\033[0m Adding Task %d - "%s"...' % (threading.current_thread().name, len(all_futures), args[0]))
    all_futures.add(executor.submit(func, *args))


def traverse_logdir(path, scan_depth):
    num_successes = 0
    errors = []
    all_logdirs = get_all_logdirs(path, scan_depth)
    all_futures = set()
    print('INFO: using %d concurrent workers to parse %d log dirs.' % (NUM_WORKERS * 2, len(all_logdirs)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS * 2) as executor:
        for dirpath in all_logdirs:
            parent, dirname = os.path.split(dirpath)
            # Folder name is like "2c4d_snort.log_workers_8_1nics_0_1493306210".
            conf, trace_file, runmode, ninstances, nnics, i, ts = dirname.split('_')
            execute(all_futures, executor, parse_eve, dirpath + '/eve.json', conf, trace_file, runmode, ninstances, nnics, i, ts)
            execute(all_futures, executor, parse_sysstat, dirpath + '/sysstat.receiver.csv', conf, trace_file, runmode, ninstances, nnics, i, ts)
            execute(all_futures, executor, parse_psstat, dirpath + '/psstat.suricata.csv', conf, trace_file, runmode, ninstances, nnics, i, ts)
        print('\033[94m[%s]\033[0m \033[92mWaiting for all tasks to complete.\033[0m' % threading.current_thread().name)
        for future in concurrent.futures.as_completed(all_futures):
            try:
                future.result()
                num_successes += 1
            except Exception as e:
                errors.append((future, str(e)))
                print(Colors.RED + 'Error: %s' % e + Colors.ENDC)
                print(traceback.format_exc())
    print(Colors.GRAY + '-' * 80 + Colors.ENDC)
    print(Colors.CYAN + 'Summary:' + Colors.ENDC)
    print(Colors.GREEN + 'Successes:\t%d' % num_successes + Colors.ENDC)
    print(Colors.RED + 'Failures:\t%d' % len(errors) + Colors.ENDC)
    for e in sorted(errors):
        print(Colors.RED + '|- %s: %s' % e + Colors.ENDC)


def main():
    data_dir = sys.argv[1]
    output_dir = sys.argv[2]
    scan_depth = int(sys.argv[3])
    try:
        os.makedirs(output_dir)
        output_dir = os.path.abspath(output_dir)
    except OSError as e:
        if e.errno != 17:
            print('Error: cannot create output path "%s": %s.' % (output_dir, str(e)))
            return 1
        else:
            output_dir = os.path.abspath(output_dir)
    try:
        os.chdir(data_dir)
    except Exception as e:
        print('Error: cannot chdir to path "%s": %s.' % (data_dir, str(e)))
        return 1        
    
    traverse_logdir('.', scan_depth)

    try:
        os.chdir(output_dir)
    except Exception as e:
        print('Error: cannot chdir to path "%s": %s. Use pwd ("%s") instead.' % (output_dir, str(e), os.getcwd()))
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS * 2) as executor:
        futures = set()
        for col in (evecollections, sysstatcollections, psstatcollections):
            for name, collection in col.items():
                futures.add(executor.submit(collection.to_xlsx))
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(Colors.RED + 'Error: %s' % e + Colors.ENDC)
                print(traceback.format_exc())
    
    os.system("grep -r 'Sample size' | sort | tee 'sample_size.txt'")


if __name__ == '__main__':
    main()
