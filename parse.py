import os
import sys
import shutil
from pathlib import Path

def test_import():
    try:
        sys.path.append('/opt/python')
        from DepthFlow import DepthScene
        DepthScene()
        return True
    except Exception as e:
        print(f"Import failed: {e}")
        return False

def main():
    print('Testing initial import...')
    if not test_import():
        print('Error: Import fails with all files present. Exiting.')
        sys.exit(1)

    lib_dir = Path('/opt/python/usr/lib64')
    temp_dir = Path('/tmp/non_essential')
    temp_dir.mkdir(exist_ok=True)

    essential_files = []

    for file in lib_dir.rglob('*'):
        if file.is_file():
            rel_path = file.relative_to(lib_dir)
            print(f'Testing {rel_path}...')
            shutil.move(str(file), str(temp_dir / file.name))
            if not test_import():
                print(f'{rel_path} is essential.')
                shutil.move(str(temp_dir / file.name), str(file))
                essential_files.append(str(rel_path))
            else:
                print(f'{rel_path} is not essential.')

    shutil.rmtree(str(temp_dir))
    
    print('Filtering complete. Essential files:')
    for file in essential_files:
        print(file)

    # Write essential files to a text file
    with open('/tmp/essential_files.txt', 'w') as f:
        for file in essential_files:
            f.write(f"{file}\n")

    print('Essential files list written to /tmp/essential_files.txt')

if __name__ == "__main__":
    main()
