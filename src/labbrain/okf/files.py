"""Reading, writing and walking the vault's files."""

import os

RESERVED = ("index.md", "log.md")


# Files a summary is built from (hashed into `sources`); everything else is an attachment.
TEXT_EXT = {
    ".md",
    ".canvas",
    ".sh",
    ".nix",
    ".lock",
    ".txt",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}


def read(vault, rel):
    with open(os.path.join(vault, rel), encoding="utf-8", newline="") as f:
        return f.read()


def write(vault, rel, text):
    with open(os.path.join(vault, rel), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def join(*parts):
    return os.path.join(*[p for p in parts if p])


def listdir(vault, d):
    """Visible subfolders and files of d, sorted."""
    try:
        entries = sorted(os.listdir(os.path.join(vault, d)), key=str.lower)
    except FileNotFoundError:
        return [], []
    dirs, files = [], []
    for e in entries:
        if e.startswith("."):
            continue
        (dirs if os.path.isdir(os.path.join(vault, d, e)) else files).append(e)
    return dirs, files


def walk(vault, d=""):
    """Yield (dir, subdirs, files) for every visible folder under d."""
    dirs, files = listdir(vault, d)
    yield d, dirs, files
    for e in dirs:
        yield from walk(vault, join(d, e))


def md_files(vault):
    return [join(d, f) for d, _, files in walk(vault) for f in files if f.endswith(".md")]


def text_files(vault):
    return [
        join(d, f)
        for d, _, files in walk(vault)
        for f in files
        if os.path.splitext(f)[1].lower() in TEXT_EXT
    ]


def is_repo_root(vault, d):
    return d == "" or os.path.exists(os.path.join(vault, d, ".git"))


def has_notes(vault, d):
    return any(
        f.endswith(".md") and f not in RESERVED for _, _, files in walk(vault, d) for f in files
    )
