"""A PC function is stored as _func_00401300 (MSVC's C names start with an underscore), but the guide tells agents to
write func_00401300, as the source does: the tools take it, and say which function it is, not "no function"."""

import json
import sqlite3
from types import SimpleNamespace

from decompnet.app.engine import core


class Store:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE functions(project_id, name, unit, status, n_insns, meta)")
        for name in ("_func_00401300", "_func_10081687"):
            self.db.execute("INSERT INTO functions VALUES(1, ?, 'text_00401000', 'open', 9, ?)",
                            (name, json.dumps({"symbol": name, "demangled": None})))

    def all(self, sql, *args):
        return self.db.execute(sql, args).fetchall()


def loose(name):
    engine = SimpleNamespace(store=Store(), _project=lambda project: {"id": 1})
    engine._loose_functions = lambda n, p: core.Core._loose_functions(engine, n, p)
    return [r["name"] for r in core.Core._loose_functions(engine, name, "game")]


def test_func_address_finds_the_underscored_function():
    assert loose("func_00401300") == ["_func_00401300"]
    assert loose("func_10081687@text_00401000") == ["_func_10081687"]
    assert loose("_func_00401300") == ["_func_00401300"]
    assert loose("func_00ABCDEF") == []
