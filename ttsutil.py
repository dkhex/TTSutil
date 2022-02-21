import json
import argparse
import shutil
from abc import abstractmethod
from pathlib import Path
from collections import defaultdict
from urllib.request import urlretrieve as download


class Cache:
    remove_symbols = {ord(s): None for s in "\{\}\"\'\\|/!?*<>:&$@`+=-"}
    default_dir = "cache"

    def __init__(self):
        pass

    def initialize(self, path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self.saved = {
            file.name: file
            for file in self.path.iterdir()
        }

    def strip_url(self, url):
        return url.translate(self.remove_symbols)

    def get_file(self, url):
        name = self.strip_url(url)
        if path := self.saved.get(name) is not None:
            return path
        path = self.path.joinpath(name)
        if self.download_file(url, path):
            self.saved[name] = path
            return path

    def download_file(self, url, path):
        try:
            download(url, path)
        except:
            print(f"Failed to download file {url}")
            return False
        else:
            return True


CACHE = Cache()


class ExtractBase:
    remove_symbols = {ord(s): None for s in "\{\}\"\'\\|/!?*<>:&$@`+="}
    default_name = "unnamed"
    default_extension = "txt"
    keep_extracted = False

    def __init__(self, attribute, path, suffix=None, extension=None, subattribute=None):
        self.attribute = attribute
        self.subattribute = subattribute
        self.path = path
        self.suffix = suffix or attribute + (f"_{subattribute}" if subattribute is not None else "")
        self.extension = extension
    
    def get_path(self, obj):
        obj_name = obj.get('Nickname').translate(self.remove_symbols) or self.default_name
        guid = obj.get('GUID')
        filename = f"{obj_name}.{guid}.{self.suffix}.{self.extension}"
        return self.path.joinpath(filename)

    def get_pathdata(self, path):
        parts = path.name.rsplit(".", maxsplit=3)
        if len(parts) < 4:
            return
        obj_name, guid, suffix, extension = parts
        return guid, suffix, obj_name

    def get_data(self, obj):
        value = obj.get(self.attribute)
        if (self.subattribute is not None) and (value is not None):
            subvalue = value.get(self.subattribute)
            if not self.keep_extracted:
                obj[self.attribute][self.subattribute] = type(subvalue)()
            return subvalue
        else:
            if not self.keep_extracted:
                obj[self.attribute] = type(value)()
            return value

    def set_data(self, obj, data):
        if self.subattribute is not None:
            if obj.get(self.attribute) is None:
                obj[self.attribute] = {}
            obj[self.attribute][self.subattribute] = data
        else:
            obj[self.attribute] = data

    @abstractmethod
    def read(self, path):
        pass

    @abstractmethod
    def save(self, obj):
        pass


class ExtractJson(ExtractBase):
    default_extension = "json"

    def read(self, path):
        with open(path, encoding="utf-8") as file:
            return json.load(file)

    def save(self, obj):
        path = self.get_path(obj)
        data = self.get_data(obj)
        with open(path, "w", encoding="utf-8", newline="\n") as file:
            json.dump(
                data, file,
                ensure_ascii=False,  # Allow store unicode symbols as is
                check_circular=False,  # Disable recurtion check (doesn't need)
                indent=2,  # Make json human readable
            )


class ExtractText(ExtractBase):
    default_extension = "lua"

    def read(self, path):
        with open(path, encoding="utf-8") as file:
            return file.read()

    def save(self, obj):
        path = self.get_path(obj)
        data = self.get_data(obj)
        with open(path, "w", encoding="utf-8", newline="\n") as file:
            file.write(data)


class ExtractFile(ExtractBase):
    default_extension = "bin"
    keep_extracted = False
    cache = CACHE  # Should be initialized first before using 

    def __init__(self):
        pass

    def get_data(self, obj):
        url = super().get_data(obj)
        path = self.cache.get_file(url)
        if path is not None:
            shutil.copy(path, self.get_path(obj))

    def set_data(self, obj, data):
        # ToDo: set file uri if file's hash not equal to hash in cache
        pass

    def read(self, path):
        pass

    def save(self, obj):
        pass


class ExtractStructure:
    def __init__(self, extractors=None):
        self.extractors = extractors or []
        self.by_attr = defaultdict(list)
        self.by_suffix = {}

    def add_extractors(self, extractors):
        self.extractors.extend(extractors)
        for e in extractors:
            self.by_attr[e.attribute].append(e)
        self.by_suffix.update({e.suffix: e for e in extractors})

    def extract(self, obj):
        for attr in obj:
            for extractor in self.by_attr.get(attr, []):
                extractor.save(obj)

    def build(self, obj_dict, path):
        guid, suffix, obj_name = self.get_pathdata(path)
        obj = obj_dict.get(guid)
        if obj is None:
            print(f"Can't find object {guid}, file '{path}' is not used")
            return
        if extractor := self.by_suffix(suffix):
            data = extractor.read(path)
            extractor.set_data(obj, data)
            if obj_name != extractor.defalut_name:
                obj['Nickname'] = obj_name


script_extractors = [
    ExtractText("LuaScript",      "scripts", "script", "lua"),
    ExtractText("LuaScriptState", "scripts", "state",  "json"),
    ExtractText("XmlUI",          "scripts", "ui",     "xml"),
]
object_extractor = ExtractStructure(script_extractors)
global_extractor = ExtractStructure(script_extractors + [
    ExtractJson("TabStates",      "base", extension="json"),
    ExtractJson("MusicPlayer",    "base", extension="json"),
    ExtractJson("CustomUIAssets", "base", extension="json"),
    ExtractJson("SnapPoints",     "base", extension="json"),
    ExtractJson("ObjectStates",   "base", extension="json"),
])


DEFAULT_NAME = "unnamed"
EXTRACTED = {
    'base': "base.json",
    'cache_dir': "cache",
    'dirs': [
        "base",
        "scripts",
    ],
}
EXTRACT_STRUCTURE = {
    # attribute: (directory, subname, extension, type)
    'LuaScript': ("scripts", "script", "lua", "text"),
    'LuaScriptState': ("scripts", "state", "json", "text"),
    'XmlUI': ("scripts", "ui", "xml", "text"),
}
EXTRACT_STRUCTURE_GLOBAL = {
    **EXTRACT_STRUCTURE,
    **{attribute: ("base", attribute, "json", "json")
    for attribute in [
        'TabStates',
        'MusicPlayer',
        'CustomUIAssets',
        'SnapPoints',
        'ObjectStates',
    ]},
}
BUILD_STRUCTURE = defaultdict(dict)
BUILD_STRUCTURE_GLOBAL = defaultdict(dict)
# for str.translate, removes invalid symbols from file name
REMOVE_SYMBOLS = {ord(s): None for s in "\"\'\\|/!?*<>:;"}


for attribute, (directory, subname, extension, typ) in EXTRACT_STRUCTURE.items():
    BUILD_STRUCTURE[directory].update({subname: (attribute, typ)})

for attribute, (directory, subname, extension, typ) in EXTRACT_STRUCTURE_GLOBAL.items():
    BUILD_STRUCTURE_GLOBAL[directory].update({subname: (attribute, typ)})


# File-related utilities
def read_json(filename):
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def save_json(filename, data, pretty=False):
    if pretty:
        indent = 2
        separators = None
    else:
        indent = None
        separators = (",", ":")
    with open(filename, "w", encoding="utf-8", newline="\n") as file:
        return json.dump(
            data,
            file,
            ensure_ascii=False,  # Allow store unicode symbols as is
            check_circular=False,  # Disable recurtion check (doesn't need)
            indent=indent,
            separators=separators
        )


def read_text(filename):
    with open(filename, encoding="utf-8") as file:
        return file.read()


def save_text(filename, text):
    with open(filename, "w", encoding="utf-8", newline="\n") as file:
        return file.write(text)


def clear_dir(path, clear_cache=False):
    orig_path = path.joinpath(EXTRACTED['base'])
    if orig_path.exists():
        orig_path.unlink()
    directories = MutableChain(EXTRACTED['dirs'])
    if clear_cache:
        directories += [EXTRACTED['cache_dir']]
    for name in directories:
        dir_path = path.joinpath(name)
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)


# Some tools for work with tree-like structure and GUIDs of TTS objects
class IDGenerator:
    """Returns next 3-byte long hex value"""

    def __init__(self, start_value=0):
        self.count = start_value

    def __call__(self):
        self.count += 1
        self.count &= 0xFFFFFF  # or 2**24-1
        return f"{self.count:06x}"


get_id = IDGenerator()


class MutableChain:
    """Special kind of chain iterator which allows adding new iterables while iterating"""

    def __init__(self, *iterables):
        self.queue = list(iterables)
        self.current = []
        if self.queue:
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
        if contained := item.get('ContainedObjects'):
            chain += contained
        if states := item.get('States'):
            chain += states.values()


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
def extract(file_path, target, dl_media=False):
    for directory in EXTRACTED['dirs']:
        path = target.joinpath(directory)
        path.mkdir()

    data = read_json(file_path)
    data["Nickname"] = "global"
    data["GUID"] = "GLOBAL"

    items_dict = flatten_items(data['ObjectStates'], fix_dupes=True)

    extract_from_items(target, items_dict, EXTRACT_STRUCTURE)
    extract_from_items(target, {'GLOBAL': data}, EXTRACT_STRUCTURE_GLOBAL)
    if dl_media:
        # ToDo:
        # cache = Cache(EXTRACTED['cache_dir'])
        # for item in items_dict.values():
        #     url = ...
        #     cache.get_file(url)
        pass

    save_json(target.joinpath(EXTRACTED['base']), data, pretty=True)


def extract_from_items(target, items_dict, structure):
    for item in items_dict.values():
        name = item.get('Nickname', "").translate(REMOVE_SYMBOLS) or DEFAULT_NAME
        for key, (directory, comp, ext, typ) in structure.items():
            if value := item.get(key):
                filename = f"{name}.{item['GUID']}.{comp}.{ext}"
                if typ == "text":
                    save_text(target.joinpath(directory, filename), value)
                else:
                    save_json(target.joinpath(directory, filename), value, pretty=True)
                # remove extracted data by replacing with empty value of same type
                item[key] = type(value)()


def extracted_iter(path):
    for file_path in path.iterdir():
        name_parts = file_path.name.rsplit(".", maxsplit=3)
        if len(name_parts) < 4:
            continue
        name, guid, comp, ext = name_parts
        yield file_path, name, guid, comp


def build_from_extracted(target, items, structure):
    for directory, components in structure.items():
        for file_path, name, guid, comp in extracted_iter(target.joinpath(directory)):
            item = items.get(guid)
            if item is None:
                continue
            if not item['Nickname'] and name != DEFAULT_NAME:
                item['Nickname'] = name
            if res := components.get(comp):
                attribute, typ = res
                if typ == "text":
                    value = read_text(file_path)
                else:
                    value = read_json(file_path)
                item[attribute] = value


# Main generate function
def build(file_path, target, pretty=False):
    data = read_json(target.joinpath(EXTRACTED['base']))

    build_from_extracted(target, {'GLOBAL': data}, BUILD_STRUCTURE_GLOBAL)
    items = flatten_items(data['ObjectStates'])
    items.update({'GLOBAL': data})
    build_from_extracted(target, items, BUILD_STRUCTURE)

    del data['Nickname']
    del data['GUID']
    save_json(file_path, data, pretty)


def get_paths(args):
    file_arg = args.extract or args.build
    file_path = Path(file_arg).with_suffix(".json")
    if args.target:
        target = Path(args.target)
    else:
        target = file_path.with_suffix("")
    return file_path, target


def main():
    parser = argparse.ArgumentParser(
        description="""
        Small utility for extracting scripts from Tabletop Simulator savefiles.
        Also it can put edited scripts back in save or create a new one based on original.
        """
    )
    parser.add_argument(
        "-e", "--extract",
        metavar="FILE",
        type=str,
        nargs="?",
        const=False,
        help="Extract data from specified savefile")
    parser.add_argument(
        "-t", "--target",
        metavar="DIR",
        type=str,
        nargs="?",
        const=False,
        help="Specify directory for extracted data")
    parser.add_argument(
        "-b", "--build",
        metavar="FILE",
        type=str,
        nargs="?",
        const=False,
        help="Build a new savefile from extracted resources")
    parser.add_argument(
        "-r", "--readable",
        action="store_true",
        help="Make building savefile human-readable (increases file size)")
    parser.add_argument(
        "-d", "--download",
        dest="download_external",
        action="store_true",
        help="Download external files")
    parser.add_argument(
        "-c", "--clear-cache",
        dest="clear_cache",
        action="store_true",
        help="Delete all downloaded files")
    parser.add_argument(
        "--cache-dir",
        dest="cache_dir",
        metavar="DIR",
        type=str,
        nargs="?",
        const=False,
        help="Specify directory for cache, may be useful if different saves use same resources")
    args = parser.parse_args()

    if args.extract and args.build:
        print("--extract and --build can't work at the same time. "
              "Such action have no sense, y'know?")
        exit(1)

    file_path, target = get_paths(args)
    CACHE.initialize(args.cache_dir or target.joinpath('cache'))
    
    if args.extract:
        if not file_path.is_file():
            print(f"Can't find file {file_path}")
            exit(1)
        target.mkdir(parents=True, exist_ok=True)
        clear_dir(target, args.clear_cache)
        extract(file_path, target, args.download_external)
        print("Extraction complete")
    elif args.build:
        if not target.joinpath(EXTRACTED['base']).exists:
            print("Specified target is not a valid extracted data")
            exit(1)
        build(file_path, target, args.readable)
        print("Building complete")
    else:
        print("Use --extract FILE or --build DIR, check --help")
        exit(1)


if __name__ == "__main__":
    main()
