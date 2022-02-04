import json
import os
import argparse


class ShortPath:
    def __init__(self, path):
        self.path = path
        
    def __add__(self, filename):    
        return os.path.join(self.path, filename)
        
    def __iter__(self):
        return iter(os.listdir(self.path))
        
    def __bool__(self):
        return os.path.exists(self.path)
        
    def init(self):
        if not self:
            os.mkdir(self.path)
            
    def clear(self):
        for file in self:
            os.remove(self + file)


SCRIPTS = ShortPath("scripts")


def read_json(filename):
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        return json.dump(data, file)


def read_text(filename):
    with open(filename, encoding="utf-8") as file:
        return file.read()


def save_text(filename, text):
    with open(filename, "w", encoding="utf-8") as file:
        return file.write(text)


def flatten_items(items):
    result = {}
    for item in items:
        result.update({item['GUID']: item})
        if 'ContainedObjects' in item:
            result.update(flatten_items(item['ContainedObjects']))
    return result


def extract(filename):
    remove_map = {ord(s): None for s in "\"\'\\|/!?*<>."}
    components = {
        'LuaScript': ("script", "lua"),
        'LuaScriptState': ("state", "lua"),
        'XmlUI': ("ui", "xml"),
    }
    
    data = read_json(filename)
    data["Nickname"] = "global"
    data["GUID"] = "GLOBAL"
    SCRIPTS.init()
    SCRIPTS.clear()
    items = flatten_items(data['ObjectStates'])
    items.update({'GLOBAL': data})
    
    for item in items.values():
        name = item.get('Nickname', "").translate(remove_map) or "unnamed"
        for key, (comp, ext) in components.items():
            if value := item.get(key):
                save_text(SCRIPTS + f"{name}.{comp}.{item['GUID']}.{ext}", value)


def build(filename, source):
    if not SCRIPTS:
        raise FileNotFoundError(f"Directory '{SCRIPTS.path}' not found. Exiting.")
    components = {
        'script': 'LuaScript',
        'state': 'LuaScriptState',
        'ui': 'XmlUI',
    }
    data = read_json(source)
    items = flatten_items(data['ObjectStates'])
    items.update({'GLOBAL': data})
    for file in SCRIPTS:
        name_parts = file.split(".")
        if len(name_parts) != 4: continue
        # name, comp, guid, extension
        _, component, guid, _ = name_parts
        if comp := components.get(component):
            items[guid][comp] = read_text(SCRIPTS + file)
    save_json(filename, data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
        Small utility for extracting scripts from Tabletop Simulator savefiles.
        Also it can put edited scripts back in save or create a new one based on original.
        """
    )
    parser.add_argument(
        "filename",
        help="Name of file which will be extracted or used as base for new build")
    parser.add_argument(
        "-b", "--build",
        type=str,
        nargs="?",
        const=False,
        help="Build a new save from extracted resources")
    args = parser.parse_args()
    
    if args.build is not None:
        build_file = args.build or args.filename
        try:
            build(build_file, args.filename)
        except FileNotFoundError as e:
            print(e)
        else:
            print("New savefile created")
    else:
        extract(args.filename)
        print("Extraction complete")
