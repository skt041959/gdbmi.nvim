import os
from pathlib import Path

from pynvim import Nvim
from pynvim.api import Buffer

from denite.base.source import Base
from denite.kind.file import Kind as FileKind
from denite.util import UserContext, Candidates


class Source(Base):
    def __init__(self, vim: Nvim) -> None:
        super().__init__(vim)

        self.name = "gdbmi-locations"
        self.kind = BreakpointKind(vim)

    def on_init(self, context: UserContext) -> None:
        self.pwd = self.vim.funcs.getcwd()
        self.locations = self.vim.vars["gdbmi_jump_locations"]

    def gather_candidates(self, context: UserContext):
        return [self._convert(e) for e in self.locations]

    def _convert(self, element):
        try:
            relpath = Path(element["filename"]).relative_to(self.pwd).as_posix()
        except ValueError:
            relpath = os.path.relpath(element["filename"], self.pwd)
            relpath = min([relpath, element["filename"]], key=len)

        candidate = {
            "word": element["text"],
            "abbr": f'{relpath[-35:]:<35.35} [{element["lnum"]:>10}] {element["number"]}: {element["text"]}',
            "action__path": element["filename"],
            "action__line": element["lnum"],
        }
        return candidate


class BreakpointKind(FileKind):
    def __init__(self, vim: Nvim) -> None:
        super().__init__(vim)

        self.name = "gdbmi-breakpoint"
        self.default_action = "jump"

    def action_jump(self, context: UserContext):
        target = context["targets"][0]
        self.vim.async_call(lambda : self.vim.call('gdbmi#util#jump', target['action__path'], target['action__line']))
