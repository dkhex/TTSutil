import json
import os
import argparse
import shutil
from pathlib import Path


def read_json(filename):
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def save_json(filename, data, pretty=False):
    with open(filename, "w", encoding="utf-8") as file:
        if pretty:
            return json.dump(data, file, indent=2, sort_keys=True)
        else:
            return json.dump(data, file)


def read_text(filename):
    with open(filename, encoding="utf-8") as file:
        return file.read()


def save_text(filename, text):
    with open(filename, "w", encoding="utf-8", newline="\n") as file:
        return file.write(text)


def clear_dir(path):
    if not path.joinpath("original.json").exist:
        return
    for item in path.iterdir():
        if item.is_file:
            shutil.unlink(item)
        elif item.is_dir:
            shutil.rmtree(item)


def flatten_items(items):
    result = {}
    for item in items:
        result.update({item['GUID']: item})
        if 'ContainedObjects' in item:
            result.update(flatten_items(item['ContainedObjects']))
    return result


def extract(file_path, target):
    remove_map = {ord(s): None for s in "\"\'\\|/!?*<>."}
    components = {
        'LuaScript': ("script", "lua"),
        'LuaScriptState': ("state", "json"),
        'XmlUI': ("ui", "xml"),
    }

    shutil.copy(file_path, target.joinpath("original.json"))

    data = read_json(file_path)
    data["Nickname"] = "global"
    data["GUID"] = "GLOBAL"
    items = flatten_items(data['ObjectStates'])
    items.update({'GLOBAL': data})
    
    for item in items.values():
        name = item.get('Nickname', "").translate(remove_map) or "unnamed"
        for key, (comp, ext) in components.items():
            if value := item.get(key):
                filename = f"{name}.{comp}.{item['GUID']}.{ext}"
                save_text(target.joinpath("scripts", filename), value)


def build(file_path, target, pretty=False):
    components = {
        'script': 'LuaScript',
        'state': 'LuaScriptState',
        'ui': 'XmlUI',
    }

    data = read_json(target.joinpath("original.json"))
    items = flatten_items(data['ObjectStates'])
    items.update({'GLOBAL': data})

    for file in target.joinpath("scripts").iterdir():
        name_parts = file.rsplit(".", maxsplit=3)
        if len(name_parts) < 4:
            continue
        # name, comp, guid, extension
        _, component, guid, _ = name_parts
        if comp := components.get(component):
            items[guid][comp] = read_text(file)
    save_json(file_path, data, pretty)


def get_paths(args):
    file_arg = args.extract or args.build
    file_path = Path(file_arg)
    if args.target:
        target = Path(args.target)
    else:
        target = file_path.parent.joinpath(file_arg.stem)
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
        help="Make building savefile human-readable (prettify), works only when --build")
    args = parser.parse_args()

    if args.extract and args.build:
        print("--extract and --build can't work at the same time. What you have made have no sense, y'know?")
        exit(1)
    elif args.extract:
        file_path, target = get_paths(args)
        target.mkdir(parents=True, exist_ok=True)
        clear_dir(target)
        extract(file_path, target)
        print("Extraction complete")
    elif args.build:
        file_path, target = get_paths(args)
        if (not target.joinpath("original.json").exists or
            not target.joinpath("scripts").exists):
            print("Specified target is not valid extracted data")
            exit(1)
        build(file_path, target, args.readable)
        print("Building complete")
    else:
        print("Use --extract FILE or --build DIR, check --help")
        exit(1)
