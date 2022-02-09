import json
import os
import argparse
import shutil
from pathlib import Path

DEFAULT_NAME = "unnamed"
EXTRACTED = {
    'base': "base.json",
    'dirs': [
        "scripts",
    ],
}
EXTRACT_STRUCTURE = {
    # key : directory, subname, extension
    'LuaScript': ("scripts", "script", "lua"),
    'LuaScriptState': ("scripts", "state", "json"),
    'XmlUI': ("scripts", "ui", "xml"),
}
BUILD_STRUCTURE = {
    'scripts': {
        'script': 'LuaScript',
        'state': 'LuaScriptState',
        'ui': 'XmlUI',
    },
}


# File-related utilities
def read_json(filename):
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def save_json(filename, data, pretty=False):
    if pretty:
        indent = 2
    else:
        indent = None
    with open(filename, "w", encoding="utf-8") as file:
        return json.dump(data, file, ensure_ascii=False, indent=indent)


def read_text(filename):
    with open(filename, encoding="utf-8") as file:
        return file.read()


def save_text(filename, text):
    with open(filename, "w", encoding="utf-8", newline="\n") as file:
        return file.write(text)


def clear_dir(path):
    orig_path = path.joinpath(EXTRACTED['base'])
    if orig_path.exists():
        orig_path.unlink()
    for name in EXTRACTED['dirs']:
        dir_path = path.joinpath(name)
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)


# Some tools for work with tree-like structure and GUIDs of TTS objects
class IDGenerator:
    """Infinite iterates all 3-byte long hex values.
    Instance can be used as an iterator and/or as a function
    """

    def __init__(self, start_value=0):
        self.count = start_value

    def __call__(self):
        self.count += 1
        self.count &= 0xFFFFFF  # or 2**24-1
        return f"{self.count:06x}"

    def __iter__(self):
        return self

    __next__ = __call__


get_id = IDGenerator()


class MutableChain:
    """Special kind of chain iterator which allows adding new iterables while iterating"""

    def __init__(self, *iterables):
        self.queue = list(iterables)
        self.current = None
        self.next_iter()

    def next_iter(self):
        if self.queue:
            self.current = iter(self.queue.pop(0))
        else:
            raise StopIteration

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            try:
                val = next(self.current)
            except StopIteration:
                self.next_iter()
            else:
                return val

    def __add__(self, iterable):
        self.queue.append(iterable)
        return self


# Useful iterators for tree-like structure of TTS objects
def iterate_items(items):
    """Iterate over all objects sorted by nesting level, roots first children last"""
    chain = MutableChain(items)
    for item in chain:
        yield item
        if 'ContainedObjects' in item:
            chain += item['ContainedObjects']


def fix_duplicate_iterator(items):
    """Iterate over given objects and assign new GUID for dupes"""
    used_guids = set()
    for item in items:
        if item['GUID'] in used_guids:
            while (new_guid := get_id()) in used_guids:
                continue
            item['GUID'] = new_guid
        used_guids.add(item['GUID'])
        yield item


def flatten_items(items, fix_dupes=False):
    """Returns dict with all objects, which can be accessed by GUID"""
    items_it = iterate_items(items)
    if fix_dupes:
        items_it = fix_duplicate_iterator(items_it)
    result = {item['GUID']: item for item in items_it}
    return result


# Main parser function
def extract(file_path, target, pretty=False):
    # for str.translate, removes invalid symbols from file name
    remove_map = {ord(s): None for s in "\"\'\\|/!?*<>."}

    clear_dir(target)
    scripts = target.joinpath("scripts")
    scripts.mkdir()

    data = read_json(file_path)
    data["Nickname"] = "global"
    data["GUID"] = "GLOBAL"
    items = flatten_items(data['ObjectStates'], fix_dupes=True)
    items.update({'GLOBAL': data})

    for item in items.values():
        name = item.get('Nickname', "").translate(remove_map) or DEFAULT_NAME
        for key, (directory, comp, ext) in EXTRACT_STRUCTURE.items():
            if value := item.get(key):
                filename = f"{name}.{item['GUID']}.{comp}.{ext}"
                save_text(target.joinpath(directory, filename), value)
                item[key] = ""

    save_json(target.joinpath(EXTRACTED['base']), data, pretty)


# Main generate function
def build(file_path, target, pretty=False):
    data = read_json(target.joinpath(EXTRACTED['base']))
    items = flatten_items(data['ObjectStates'])
    items.update({'GLOBAL': data})

    for directory, components in BUILD_STRUCTURE.items():
        for file in target.joinpath(directory).iterdir():
            name_parts = file.name.rsplit(".", maxsplit=3)
            if len(name_parts) < 4:
                continue
            # name, guid, component, extension
            name, guid, component, _ = name_parts
            item = items.get(guid)
            if item is None:
                print(f"Can't find object with guid '{guid}', file '{file}' not used")
                continue
            if not item['Nickname'] and name != DEFAULT_NAME:
                item['Nickname'] = name
            if comp := components.get(component):
                items[guid][comp] = read_text(file)

    del data['Nickname']
    del data['GUID']
    save_json(file_path, data, pretty)


def get_paths(args):
    file_arg = args.extract or args.build
    file_path = Path(file_arg)
    if args.target:
        target = Path(args.target)
    else:
        target = file_path.parent.joinpath(file_path.stem)
    return file_path, target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
        Small utility for extracting scripts from Tabletop Simulator savefiles.
        Also it can put edited scripts back in save or create a new one based on original.
        """
    )
    parser.add_argument(
        "-e", "--extract",
        type=str,
        nargs="?",
        const=False,
        help="Extract data from specified savefile")
    parser.add_argument(
        "-t", "--target",
        type=str,
        nargs="?",
        const=False,
        help="Specify directory for extracted data")
    parser.add_argument(
        "-b", "--build",
        type=str,
        nargs="?",
        const=False,
        help="Build a new savefile from extracted resources")
    parser.add_argument(
        "-r", "--readable",
        action="store_true",
        help="Make building savefile human-readable (prettify), for --extracted formats 'base.json'")
    args = parser.parse_args()

    if args.extract and args.build:
        print("--extract and --build can't work at the same time. Such action have no sense, y'know?")
        exit(1)
    elif args.extract:
        file_path, target = get_paths(args)
        target.mkdir(parents=True, exist_ok=True)
        clear_dir(target)
        extract(file_path, target, args.readable)
        print("Extraction complete")
    elif args.build:
        file_path, target = get_paths(args)
        if not target.joinpath(EXTRACTED['base']).exists:
            print("Specified target is not valid extracted data")
            exit(1)
        build(file_path, target, args.readable)
        print("Building complete")
    else:
        print("Use --extract FILE or --build DIR, check --help")
        exit(1)
