#!/usr/bin/env python3
"""A script for finding and extracting Apple Dictionary files."""
from typing import Optional

import os
import zlib

from collections import Counter
from pathlib import Path

import click

from bs4 import BeautifulSoup

DEBUG = False
INT_SIZE = 4  # Number in the raw bytes are 32-bit little-endian integers
HEADER_FIELD_SEP = b"\xff\xff\xff\xff"
DEFAULT_BASE = (
    "/System/Library/AssetsV2/"
    "com_apple_MobileAsset_DictionaryServices_dictionaryOSX/"
)


def to_int(number: bytes, *, byteorder: str = "little") -> int:
    return int.from_bytes(number, byteorder=byteorder)


def split_entries(content: bytes) -> list[str]:
    """Split the content into entries.

    :param content: An uncompress
    :return: A list of XML strings.
    """
    entries = []
    while content:
        length = to_int(content[:INT_SIZE])
        entries.append(content[INT_SIZE : length + INT_SIZE].decode("UTF-8"))
        content = content[INT_SIZE + length :]
    return entries


def process_chunk(compressed_chunk: bytes, strict: bool = True) -> list[str]:
    """Expand and extract entries from the chunk.

    :param compressed_chunk: A compress byte string containing a zip.
    :param strict: Check that the size matches , defaults to True

    :return: A list of XML entry strings from the chunk.
    """
    # Uncompressed size of chunk (4 bytes)
    uncompressed_size = to_int(compressed_chunk[:INT_SIZE])

    decompressobj = zlib.decompressobj()
    content_decompressed = decompressobj.decompress(compressed_chunk[INT_SIZE:])
    if strict:
        assert len(decompressobj.unused_data) == 0
        # Verify size
        assert len(content_decompressed) == uncompressed_size

    return split_entries(content_decompressed)


def extract_chunks(
    content: bytes,
    num_chunks: int,
) -> tuple[list[str], int]:
    """Take an uncompressed chunk and split it into a list of XML strings.

    :param content: An uncompressed string of bytes.
    :param num_chunks: How many chunks are in the content.

    :return: A list of UTF-8 XML strings of dictionary entries.
    """
    entries = []
    content_size = 0
    for i in range(num_chunks):
        # This seems like a bug in the file format having the size twice,
        # maybe it was added to a wrapper twice or the like.
        # Chunk size excluding 8 bytes
        _chunk_size_1 = to_int(content[:INT_SIZE])  # noqa Unused
        # Chunk size with the uncompressed size
        chunk_size = to_int(content[INT_SIZE : INT_SIZE * 2])
        # Content size plus 2 size headers
        content_size += chunk_size + INT_SIZE * 2
        content = content[INT_SIZE * 2 :]
        compressed_chunk, content = (
            content[:chunk_size],
            content[chunk_size:],
        )

        chunk_entries = process_chunk(compressed_chunk)
        entries.extend(chunk_entries)
        if not DEBUG:
            continue
        click.echo(
            f"Chunk #{i + 1}/{num_chunks}: {len(chunk_entries):03,} entries.", err=True
        )

    return entries, content_size


def find_zip(content_bytes: bytes) -> tuple[bytes, bytes]:
    """Exploratory function for finding embedded zip chunks.

    :param content_bytes: The file contents.
    :returns: The extracted, decompressed chunk, and the remainder of the string.
    """
    stripped_bytes = b""
    idx = 0
    while True:
        decompressobj = zlib.decompressobj()
        try:
            content_decompressed = decompressobj.decompress(content_bytes)
            break
        except zlib.error:
            stripped_bytes += content_bytes[:1]
            idx += 1
            content_bytes = content_bytes[1:]

    byte_string = "".join(f"{i:02x}" for i in stripped_bytes)
    if DEBUG:
        click.echo(f"The discarded bytes were: {byte_string}", err=True)
    return content_decompressed, decompressobj.unused_data


def process_body_data(content_bytes: bytes) -> list[str]:
    """Process Body.data file for Apple Dictionaries.

    The file format is:
    Header (96 bytes long)
        \x00 padding (64 bytes)
        content size (4 bytes)
        HEADER_FIELD_SEP (4 bytes)
        header size (4 bytes)
        0 (4 bytes)
        number of chunks in the file (4 bytes)
        HEADER_FIELD_SEP * 2 (8 bytes)
    Chunks (numer of chunks in the file long)
        Chunk size [+8 bytes] (4 bytes)
        Chunk size 2 [+4 bytes] (4 bytes)
        Uncompressed chunk size (4 bytes)
        zlib chunk (Chunk size 2 - 4 bytes long)
        ...
        Chunk size [+8 bytes] (4 bytes)
        Chunk size 2 [+4 bytes] (4 bytes)
        Uncompressed chunk size (4 bytes)
        zlib chunk (Chunk size 2 - 4 bytes long)
    \x00 padding (presumably to fill the remaining space in the final chunk)

    :param content_bytes: A byte-string of the file contents.
    :return: A list of UTF-8 XML strings for entries.
    """
    entries: list[str] = []

    header_bytes = content_bytes[:96]
    content_bytes = content_bytes[96:]
    header_values = [
        to_int(header_bytes[idx - INT_SIZE : idx])
        for idx in range(len(header_bytes), 1, -INT_SIZE)
        if header_bytes[idx - INT_SIZE : idx] != HEADER_FIELD_SEP
    ]
    num_chunks = header_values[0]
    header_size = header_values[2]
    header_content_size = header_values[4]

    # Check that the remainder of the header is all \x00's
    zero_pad = Counter(header_bytes[:-header_size])[0]
    assert zero_pad == len(header_bytes) - header_size

    entries, content_size = extract_chunks(content_bytes, num_chunks)
    # Check that we got the expected amount of content
    # and that that end of the file is \x00 padded.
    content_bytes = content_bytes[content_size:]
    content_size += header_size
    assert Counter(content_bytes)[0] == len(content_bytes)
    assert content_size == header_content_size

    return entries


def extract_body_data(
    content_bytes: bytes,
    outfile: Optional[Path] = None,
    *,
    prettify: bool = True,
) -> None:
    """Extract entries and save them to a file or print them to the console.

    :param content_bytes: The Body.data file contents.
    :param outfile: The location to save the data, defaults to printing to the screen.
    :param prettify: Format the file contents with BS4, defaults to True
    """
    entries = process_body_data(content_bytes)

    dictionary_text = (
        "<d:dictionary "
        'xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng">'
        + "".join(entries)
        + "</d:dictionary>"
    )
    if prettify:
        if DEBUG:
            click.echo("Prettifying XML for {out_file.stem}", err=True)
        dictionary_text = BeautifulSoup(dictionary_text, "lxml-xml").prettify()

    if DEBUG:
        click.echo(
            f"Writing XML to {outfile}: Found {len(entries):,} entries", err=True
        )
    if not outfile:
        click.echo(dictionary_text, err=False)  # Output to stdout
    else:
        outfile.write_text(dictionary_text)


def get_dictionaries(base: Path) -> list[tuple[str, list[Path]]]:
    """Make a list of available dictionaries and the interesting files.

    :param base: The Apple Dictionaries root directory.
    :return: A list of tuples of name, files for each dictionary.
    """
    all_dicts = sorted(
        (
            (
                dic.stem,
                [
                    f
                    for f in (dic / "Contents" / "Resources").iterdir()
                    if f.suffix != ".lproj"
                ],
            )
            for dic_path in Path(base).iterdir()
            if dic_path.is_dir()
            for dic in (dic_path / "AssetData").iterdir()
        ),
        key=lambda x: x[0],
    )
    return [(name, files) for name, files in all_dicts if files]


def get_type() -> type:
    """:return: a choice of dictionaries names or just accept a string."""
    base = Path(os.environ.get("DICT_BASE", DEFAULT_BASE))
    if not base.exists():
        return str
    else:
        return click.Choice(["all"] + [name for name, _ in get_dictionaries(base)])


@click.command()
@click.option(
    "--base",
    type=click.Path(exists=True, file_okay=False, readable=True),
    default=DEFAULT_BASE,
    help=(
        "The root directory of the OS X dictionaries. "
        f"(Default: {DEFAULT_BASE}) [Env var DICT_BASE]"
    ),
)
@click.option(
    "--out",
    type=click.Path(exists=True, file_okay=False, writable=True),
    default=None,
    help="The path to place extracted XML files.",
)
@click.option(
    "--dictionary",
    "-d",
    type=get_type(),
    multiple=True,
    default=["all"],
    help="The dictionary to extract or 'all'. (Default: all) [Accepts multiple]",
)
@click.option(
    "--format-xml/--no-format-xml",
    default=False,
    is_flag=True,
    help="Format the XML files using BeautifulSoup. (Default: False)",
)
@click.option(
    "--debug",
    default=False,
    is_flag=True,
    help="Output debug information to STDERR. (Default: False)",
)
def main(
    base: str,
    out: Optional[str],
    dictionary: list[str],
    format_xml: bool,
    debug: bool,
) -> None:
    """Extract XML from Apple Dictionary files."""
    global DEBUG
    DEBUG = debug

    dictionaries = get_dictionaries(Path(base))
    if "all" in dictionary:
        extract_dictionaries = dictionaries
    else:
        extract_dictionaries = [
            (name, files) for name, files in dictionaries if name in dictionary
        ]

    for idx, (name, files) in enumerate(extract_dictionaries):
        # Files of interest:
        #  - KeyText.data
        #  - EntryID.data
        #  - KeyText.index
        #  - EntryID.index
        #  - Body.data
        #  - DefaultStyle.css
        files = [f for f in files if f.name == "Body.data"]
        if not files:
            continue
        file = files[0]

        if DEBUG:
            click.echo(f"Processing file: {name}/{file.name}", err=True)
        extract_body_data(
            file.read_bytes(),
            Path(out).resolve() / (name + ".xml") if out else None,
            prettify=format_xml,
        )
        if not DEBUG:
            continue
        click.echo(f"Processed {name}: {idx+1}/{len(extract_dictionaries)}.", err=True)


if __name__ == "__main__":
    main(auto_envvar_prefix="DICT")
