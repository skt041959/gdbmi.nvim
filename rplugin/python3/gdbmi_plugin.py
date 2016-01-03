import logging
import traceback

import neovim

from gdbmi import Session


@neovim.plugin
class GDBMI_plugin():
    def __init__(self, vim):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.vim = vim

        self.session = None

    def _error(self, msg):
        self.vim.call('gdbmi#util#print_error', msg)

    @neovim.command('GdbmiInitializePython', sync=True, nargs=0)
    def init_python(self):
        self.vim.vars['gdbmi#_channel_id'] = self.vim.channel_id

    @neovim.rpc_export('launchgdb')
    def launchgdb(self, debugee):
        self.session = Session(debugee)
        self.session.launch()

    @neovim.rpc_export('breakswitch')
    def breakswitch(self, bufnr, line):
        for b in self.vim.buffers:
            if b.number == bufnr:
                filename = b.name
                break
        self.session.breakswitch(name, line)


def main(debugee):
    session = Session(debugee)

if __name__ == "__main__":
    import sys
    main(sys.argv[1])

