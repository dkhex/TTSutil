# TTSutil
Small utility to extract and put back scripts from Tabletop Simulator savefiles


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

If you want get formatted save - add `--readable` when building:
```bash
python ttsutil.py --readable --build Saves/TS_Save_1.json
```

If `--target` not specified, script uses directory with name of file without extension
