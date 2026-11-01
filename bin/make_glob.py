#!/usr/bin/env python3

import hashlib
import sys
from pathlib import Path
from urllib.parse import quote

from noun import Cell, deep, intbytes, mug

MIME_TYPES = {
    "css": "text/css",
    "gif": "image/gif",
    "html": "text/html",
    "ico": "image/x-icon",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "js": "application/javascript",
    "json": "application/json",
    "png": "image/png",
    "svg": "image/svg+xml",
    "ttf": "font/ttf",
    "webmanifest": "application/manifest+json",
    "woff": "font/woff",
    "woff2": "font/woff2",
}
BASE32 = "0123456789abcdefghijklmnopqrstuv"


class BitWriter:
    def __init__(self):
        self.output = bytearray()
        self.buffer = 0
        self.used = 0
        self.cursor = 0

    def write(self, value, count):
        if count == 0:
            return
        self.buffer |= value << self.used
        self.used += count
        self.cursor += count
        byte_count = self.used // 8
        if byte_count:
            self.output.extend(self.buffer.to_bytes((self.used + 7) // 8, "little")[:byte_count])
            self.buffer >>= byte_count * 8
            self.used -= byte_count * 8

    def finish(self):
        if self.used:
            self.output.append(self.buffer)
            self.buffer = 0
            self.used = 0
        return bytes(self.output)


def jam_bytes(value):
    writer = BitWriter()
    references = {}

    def save(noun):
        references[noun] = writer.cursor

    def mat(atom):
        if atom == 0:
            writer.write(1, 1)
            return
        atom_length = atom.bit_length()
        length_size = atom_length.bit_length()
        writer.write(1 << length_size, length_size + 1)
        writer.write(atom_length & ((1 << (length_size - 1)) - 1), length_size - 1)
        writer.write(atom, atom_length)

    def back(reference):
        writer.write(3, 2)
        mat(reference)

    def serialize(noun):
        duplicate = references.get(noun)
        if deep(noun):
            if duplicate is not None:
                back(duplicate)
                return
            save(noun)
            writer.write(1, 1)
            writer.write(0, 1)
            serialize(noun.head)
            serialize(noun.tail)
            return
        if duplicate is not None:
            atom_size = noun.bit_length()
            reference_size = duplicate.bit_length()
            if atom_size >= reference_size:
                back(duplicate)
                return
        save(noun)
        writer.write(0, 1)
        mat(noun)

    serialize(value)
    return writer.finish()


def cord(value):
    return int.from_bytes(value.encode(), "little")


def path_noun(parts):
    result = 0
    for part in reversed(parts):
        result = Cell(cord(part), result)
    return result


def dor(a, b):
    if a == b:
        return True
    if deep(a):
        if not deep(b):
            return False
        if a.head == b.head:
            return dor(a.tail, b.tail)
        return dor(a.head, b.head)
    if deep(b):
        return True
    return a < b


def gor(a, b):
    a_mug = mug(a)
    b_mug = mug(b)
    return dor(a, b) if a_mug == b_mug else a_mug < b_mug


def map_put(tree, entry):
    if tree == 0:
        return Cell(entry, Cell(0, 0))
    node = tree.head
    if entry.head == node.head:
        return Cell(entry, tree.tail)
    left = tree.tail.head
    right = tree.tail.tail
    if gor(entry.head, node.head):
        return Cell(node, Cell(map_put(left, entry), right))
    return Cell(node, Cell(left, map_put(right, entry)))


def shas(salt, serialized):
    value_hash = int.from_bytes(hashlib.sha256(serialized).digest(), "little")
    length = max(32, len(intbytes(salt)))
    digest = hashlib.sha256((salt ^ value_hash).to_bytes(length, "little")).digest()
    return int.from_bytes(digest, "little")


def sham(serialized):
    hashed = shas(cord("sham"), serialized)
    mask = (1 << 128) - 1
    return (hashed & mask) ^ (hashed >> 128)


def scow_uv(value):
    if value == 0:
        return "0v0"
    digits = []
    while value:
        value, digit = divmod(value, 32)
        digits.append(BASE32[digit])
    digits = "".join(reversed(digits))
    first_length = (len(digits) - 1) % 5 + 1
    groups = [digits[:first_length]]
    groups.extend(digits[i:i + 5] for i in range(first_length, len(digits), 5))
    return "0v" + ".".join(groups)


def file_entry(root, file_path):
    relative = file_path.relative_to(root)
    parts = []
    for part in relative.parts:
        parts.extend(quote(segment, safe="-_~") for segment in part.split("."))
    extension = relative.suffix.removeprefix(".").lower()
    if extension not in MIME_TYPES:
        raise ValueError(f"no MIME type configured for {relative}")
    data = file_path.read_bytes()
    mime = Cell(path_noun(MIME_TYPES[extension].split("/")), Cell(len(data), int.from_bytes(data, "little")))
    return Cell(path_noun(parts), mime)


def make_glob(source, destination):
    root = Path(source)
    files = sorted((path for path in root.rglob("*") if path.is_file()), key=lambda path: path.as_posix())
    if not (root / "index.html").is_file():
        raise ValueError("glob source must contain index.html")
    glob = 0
    for file_path in files:
        glob = map_put(glob, file_entry(root, file_path))
    serialized = jam_bytes(glob)
    glob_hash = scow_uv(sham(serialized))
    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    filename = f"glob-{glob_hash}.glob"
    (output / filename).write_bytes(serialized)
    (output / "hash").write_text(glob_hash + "\n")
    print(filename)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} SOURCE_DIRECTORY OUTPUT_DIRECTORY")
    make_glob(sys.argv[1], sys.argv[2])
