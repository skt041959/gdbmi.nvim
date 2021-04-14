from pynvim import Nvim

from denite.util import UserContext, Candidates
from denite.kind.file import Kind as Base

class Kind(Base):
    def __init__(self, vim: Nvim) -> None:
        super().__init__(vim)

        self.name = "gdbmi-breakpoint"
        self.default_action = "jump"

    def action_jump(self, context: UserContext):
        target = context["targets"][0]
        self.vim.async_call(lambda : self.vim.call('gdbmi#util#jump', target['action__path'], target['action__line']))
