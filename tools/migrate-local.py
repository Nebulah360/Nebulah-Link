#!/usr/bin/env python3
"""Copy saved Nebulah Link data to a new folder without replacing existing data."""
import argparse
import hashlib
import shutil
import tempfile
from pathlib import Path


SAVED = ('companion.sqlite3', 'games.sqlite3', 'repositories.sqlite3',
         'app-settings.json', 'launcher-settings.json', 'game-data.json')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.digest()


def migrate(old, new, apply=False):
    old, new = Path(old).resolve(), Path(new).resolve()
    if old == new or not old.is_dir() or not new.is_dir():
        raise ValueError('Choose two different existing app folders.')
    source, target = old / '.local', new / '.local'
    if not source.is_dir():
        raise ValueError('The old app folder has no .local data.')
    if target.is_symlink() or source.is_symlink():
        raise ValueError('Linked .local folders are not supported.')
    if apply:
        target.mkdir(exist_ok=True)
    results = []
    for name in SAVED:
        before, after = source / name, target / name
        if before.is_symlink() or after.is_symlink():
            raise ValueError('Linked saved-data files are not supported.')
        if not before.is_file():
            continue
        if any((source / (name + suffix)).exists() for suffix in ('-wal', '-shm')):
            raise ValueError('Stop the old bridge and close its database before migrating.')
        if after.exists():
            results.append((name, 'already present' if after.is_file() and digest(before) == digest(after)
                            else 'conflict: destination kept'))
            continue
        if not apply:
            results.append((name, 'ready to copy'))
            continue
        # shortcut: require both bridges stopped; no concurrent destination writer is supported.
        with tempfile.NamedTemporaryFile(dir=target, prefix='.migrate-', delete=False) as stage:
            staged = Path(stage.name)
        try:
            shutil.copyfile(before, staged)
            if digest(before) != digest(staged):
                raise OSError('Saved-data copy did not match its source.')
            if after.exists():
                results.append((name, 'conflict: destination kept'))
            else:
                staged.replace(after)
                results.append((name, 'copied'))
        finally:
            staged.unlink(missing_ok=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old_app_folder')
    parser.add_argument('new_app_folder')
    parser.add_argument('--apply', action='store_true', help='Copy missing saved files after reviewing the default plan.')
    args = parser.parse_args()
    try:
        for name, state in migrate(args.old_app_folder, args.new_app_folder, args.apply):
            print(f'{name}: {state}')
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
