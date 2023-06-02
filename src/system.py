import os
import glob
import shutil
import random
import re

def exists(path):
    return os.path.exists(path)


def mkdir(p):
    os.makedirs(p)

def delete(p):
    if exists(p):
        os.remove(p)


def ls_files(directory, ext='', with_path=True):
    onlyfiles = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    if not ext == '':
        extt = '.' + ext
        out = []
        for p in onlyfiles:
            if os.path.splitext(p)[1] == extt:
                out.append(p)
    else:
        out = onlyfiles
    if with_path:
        for i in range(len(out)):
            out[i] = os.path.join(directory, out[i]).replace('\\', '/')
    return out


def ls_dirs(directory, with_path=True):
    out = [f for f in os.listdir(directory) if not os.path.isfile(os.path.join(directory, f))]
    if with_path:
        for i in range(len(out)):
            out[i] = os.path.join(directory, out[i])
    return out


def ls_files_recursively(directory, ext=None, with_path=True):
    if ext:
        key = "**/*." + ext
    else:
        key = '**'
    out = glob.glob(os.path.join(directory, key), recursive=True)
    if not with_path:
        for i in range(len(out)):
            out[i] = os.path.relpath(out[i], directory)
    for i in range(len(out)):
        out[i] = replace_backslash(out[i])
        if out[i][0] == '/':
            out[i] = out[1:]
    return out


# Util path
def basename(path):
    return os.path.splitext(os.path.basename(path))[0]


def noExt(path):
    return os.path.splitext(path)[0]


def noDir(path):
    return os.path.basename(path)


def dirname(file):
    return os.path.dirname(file)


def ext(path):
    return os.path.splitext(path)[1][1:]


# Use for naming rules for data results
def add_suffix(path, sufix='', n_ext=''):
    if sufix=='':
        if n_ext=='':
            return path
        else:
            return noExt(path)  + '.' + n_ext
    else:
        if n_ext=='':
            return noExt(path) + '_' + sufix + '.' + ext(path)
        else:
            return noExt(path) + '_' + sufix + '.' + n_ext


def replace_backslash(path):
    return path.replace('\\', '/')


# Not very usefull
def join(p1, p2, p3='', p4='', p5='', p6=''):
    if p3 == '':
        return os.path.join(p1, p2).replace('\\', '/')
    if p4 == '':
        return os.path.join(p1, p2, p3).replace('\\', '/')
    if p5 == '':
        return os.path.join(p1, p2, p3, p4).replace('\\', '/')
    if p6 == '':
        return os.path.join(p1, p2, p3, p4, p5).replace('\\', '/')
    return os.path.join(p1, p2, p3, p4, p5, p6).replace('\\', '/')


# Could be better
def get_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size / 1000000

def copy_files(src_dir, dst_dir, src_prefix_list=[], dst_new_prefix=None, shuffle_src=False):
    """
    Copy files from src_dir to dst_dir
    src_prefix_list: select src files with prefix in this list, use [] to select all src files 
    dst_new_prefix: dst files are renamed to {dst_new_prefix}.{index_from_0_to_n}.{extension}, use None to keep the same names as src files
    shuffle_src: shuffle src files before copying
    """
    if not exists(dst_dir):
        mkdir(dst_dir)

    # Gather src files
    if (len(src_prefix_list) == 0):
        src_files = glob.glob(join(src_dir, '*'))
    else:
        if not isinstance(src_prefix_list, list):
            print("ERROR: src_prefix_list must be a list")
            return
        src_files = []
        for src_prefix in src_prefix_list:
            src_files += glob.glob(join(src_dir, f"{src_prefix}*"))

    # Shuffle src files
    if shuffle_src:
        random.shuffle(src_files)

    # Copy to dst_dir, use copy2 to copy also metadata
    if dst_new_prefix is None:
        for src_file in src_files:
            shutil.copy2(src_file, dst_dir)
    else:
        for i, src_file in enumerate(src_files):
            file_ext = ext(src_file)
            shutil.copy2(src_file, join(dst_dir, f"{dst_new_prefix}.{i}.{file_ext}"))

def move_files(src_dir, dst_dir, sort_src_by_digits=False, start_pos=None, end_pos=None):
    """
    Move files from src_dir to dst_dir
    sort_by_digit: sort the src file by digits in file name before moving
    start_pos and end_pos: select files in this range to move
    """
    if not exists(dst_dir):
        mkdir(dst_dir)

    # Gather src files
    if not sort_src_by_digits:
        src_files = glob.glob(join(src_dir, '*'))
    else:
        regex = '\d+' # regular expression to find digits
        src_files = sorted(glob.glob(join(src_dir, '*')), key=lambda x:float(re.findall(regex, x)[0]))
        
    if (start_pos is None) or (end_pos is None):
        for src_file in src_files:
            shutil.move(src_file, dst_dir)        
    else:
        if (start_pos < 0) or (end_pos > len(src_files)) or (start_pos >= end_pos):
            print("ERROR: start_pos and end_pos invalid")
            return
        else:
            for i in range(start_pos, end_pos):
                shutil.move(src_files[i], dst_dir)