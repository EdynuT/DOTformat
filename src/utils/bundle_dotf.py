"""Utility functions to bundle and unbundle multiple .dotf encrypted artifacts.

Adapted from the former Encrypter project's file_transform module, with safety
checks to prevent directory traversal.

Functions:
    bundle_dotf_files(input_folder: Path, output_file: Path) -> Path
    unbundle_dotf_file(bundle_file: Path, output_folder: Path) -> None

Format per entry:
    [4 bytes size big-endian][filename UTF-8][0x00][raw file bytes]
A companion index.txt is written beside the bundle to map stored filename to
original basename (mirrors legacy behavior for transparency).
"""
from __future__ import annotations
from pathlib import Path
import os

__all__ = ["bundle_dotf_files", "unbundle_dotf_file"]

def bundle_dotf_files(input_folder: Path, output_file: Path) -> Path:
    input_folder = input_folder.resolve()
    output_file = output_file.resolve()
    index_file = output_file.parent / 'index.txt'
    with index_file.open('w', encoding='utf-8') as index, output_file.open('wb') as bundle:
        for root, _, files in os.walk(input_folder):
            for name in files:
                if not name.endswith('.dotf'):
                    continue
                fp = Path(root) / name
                # Security: avoid escaping the input folder
                if not str(fp.resolve()).startswith(str(input_folder)):
                    continue
                data = fp.read_bytes()
                bundle.write(len(data).to_bytes(4, 'big'))
                bundle.write(name.encode('utf-8'))
                bundle.write(b'\0')
                bundle.write(data)
                index.write(f"{name}\t{fp.name}\n")
    return output_file

def unbundle_dotf_file(bundle_file: Path, output_folder: Path) -> None:
    bundle_file = bundle_file.resolve()
    output_folder = output_folder.resolve()
    index_file = bundle_file.parent / 'index.txt'
    if not index_file.exists():
        raise FileNotFoundError(f"Index file not found: {index_file}")
    mapping = {}
    with index_file.open('r', encoding='utf-8') as index:
        for line in index:
            if '\t' in line:
                stored, original = line.rstrip().split('\t', 1)
                mapping[stored] = original
    with bundle_file.open('rb') as bundle:
        while True:
            sz_bytes = bundle.read(4)
            if not sz_bytes:
                break
            size = int.from_bytes(sz_bytes, 'big')
            name_bytes = bytearray()
            while True:
                b = bundle.read(1)
                if not b:
                    raise IOError("Corrupt bundle (unexpected EOF in name)")
                if b == b'\0':
                    break
                name_bytes.extend(b)
            stored_name = name_bytes.decode('utf-8')
            data = bundle.read(size)
            out_name = mapping.get(stored_name, stored_name)
            out_path = output_folder / out_name
            if not str(out_path.parent.resolve()).startswith(str(output_folder)):
                continue
            out_path.write_bytes(data)
