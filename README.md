# TTSutil
Small utility to extract and put back scripts from Tabletop Simulator savefiles

## Features

- split save to separate files
- go through all objects and it's ContainedObjects
- fixes duplicating GUIDs
- take LuaScript, LuaScriptState, XmlUI from objects and save it to `extracted/scripts/`
- move content of CustomUIAssets, MusicPlayer, SnapPoints, TabStates and ObjectStates to `extracted/base/`
- leave rest part of save in `extracted/base.json`
- build save from `extracted/` directory

Names of extracted files is contains 4 parts separated by dot:
`name.GUID.attrtype.extension`

You can create new file or delete existing and it will be applied to object's attribute by GUID and corresponding attribute type.

## Usage

To extract data from `Saves/TS_Save_1.json` to `Saves/TS_Save_1/` directory:
```bash
python ttsutil.py --extract Saves/TS_Save_1.json
```

You can specify extract location with `--target` option:
```bash
python ttsutil.py --extract Saves/TS_Save_1.json --target OtherLoc/extracted/
```

To build from extracted data:
```bash
python ttsutil.py --build Saves/New_Save.json --target OtherLoc/extracted/
```

If `--target` not specified, script uses directory with name of file without extension
```bash
python ttsutil.py --build Saves/TS_Save_1.json  # Will use Saves/TS_Save_1/ as target
```
