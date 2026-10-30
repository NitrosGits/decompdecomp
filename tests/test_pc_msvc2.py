"""Visual C++ 2.x (1994-96) for Windows PC games: it predates the Rich header, so a game it built is named by its
linker's version (2.50 for 2.0, 2.55 for 2.1 and 2.2), and its compilers come from discs the user owns (toolchains.toml
`local` parts) that decompdecomp can't download. The end-to-end part runs only where `msvc2` was installed."""

import struct
import subprocess
import sys
from pathlib import Path

import pytest

from decompnet import consoles, toolchains
from decompnet.consoles.pc import MSVC_VERSIONS, scratch

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "projects" / "demo-pc"


def pe(linker: tuple[int, int]) -> bytes:
    """The smallest PE header describing a 32-bit x86 program with a given linker version, and no Rich header."""
    at = 0x80
    head = bytearray(at) + b"PE\0\0" + struct.pack("<HHIIIHH", 0x14C, 0, 0, 0, 0, 0xE0, 0x103)
    optional = bytearray(0xE0)
    struct.pack_into("<H", optional, 0, 0x10B)
    optional[2:4] = bytes(linker)
    head[0x3C:0x40] = struct.pack("<I", at)
    head[:2] = b"MZ"
    return bytes(head + optional)


@pytest.mark.parametrize("linker, version", [((2, 50), "2.0"), ((2, 55), "2.2")])
def test_a_program_with_a_2x_linker_and_no_rich_header_names_its_visual_cpp(linker, version):
    build = scratch.describe(pe(linker))
    assert build.version == version and build.build is None
    assert build.pack_version == version and not build.blockers() and not build.cannot_match()
    assert "Visual C++ " + version in build.summary()


def test_the_2x_versions_are_in_the_console_and_come_from_one_pack():
    pc = consoles.get("pc")
    assert {"MSVC/2.0", "MSVC/2.1", "MSVC/2.2"} <= {c.id for c in pc.compilers}
    assert [scratch.compiler_pack(v.removeprefix("MSVC/")) for v in MSVC_VERSIONS[:3]] == ["msvc2"] * 3
    assert scratch.MSVC_PACKS[0] == "msvc"  # (an older project's configure.py keeps only the last --msvc: the 6.0 pack's)


def test_the_discs_are_the_users_to_supply(tmp_path, monkeypatch):
    monkeypatch.setenv("DECOMPNET_TOOLCHAINS", str(tmp_path))
    with pytest.raises(toolchains.ToolchainError, match=r"disc image.*sha256 f97defed.*msvc20\.iso"):
        toolchains.install("msvc2", accept_license=True)
    assert toolchains.installed("msvc2") is None


@pytest.mark.skipif(toolchains.installed("msvc2") is None or toolchains.installed("wibo") is None
                    and sys.platform != "win32", reason="needs Visual C++ 2.x (your own discs: msvc2) and wibo")
@pytest.mark.parametrize("version, linker", [("2.0", (2, 50)), ("2.2", (2, 55))])
def test_demo_quest_built_by_2x_is_named_by_its_linker(version, linker):
    done = subprocess.run([sys.executable, str(DEMO / "build.py"), version], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    exe = (DEMO / "build" / version / "demoquest.exe").read_bytes()
    assert b"Rich" not in exe[:0x400]
    assert scratch.describe(exe).pack_version == version


def test_a_2x_project_is_built_with_ox_and_no_exception_flag():
    """2.x's cl knows /GX only (/EHsc warns on every file), and a 1995 game matches with /Ox: /O2 pools string
    literals and uses COMDATs (found on a real game, whose hand-made project matches 95% of it)."""
    template = (scratch.TEMPLATE / "tools" / "configure.py").read_text(encoding="utf-8")
    text = scratch.flags_for_pack(template, "msvc2")
    assert 'CL_FLAGS = ["/nologo", "/c", "/Ox", "/Gy"]' in text and "/EHsc" not in text and "/O2" not in text.split("CL_FLAGS")[1].split("\n")[0]
    assert '"/O2"' in scratch.flags_for_pack(template, "msvc")  # (the other packs keep theirs)
    assert '"/EHsc"' in scratch.flags_for_pack(template, "msvc2005")
