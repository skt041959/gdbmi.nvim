import logging
import traceback
import os

import neovim

from .gdbmi.session import Session


@neovim.plugin
class GDBMI_plugin():
    def __init__(self, vim):
        self.vim = vim

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.logger.debug('[gdbmi] instance init')

        self.session = None

    def _error(self, msg):
        self.vim.call('gdbmi#util#print_error', msg)
        # self.logger.critical(traceback.format_exc())

    @neovim.command('GdbmiInitializePython', sync=True, nargs=0)
    def init_python(self):
        self.vim.vars['gdbmi#_python_pid'] = os.getpid()
        self.vim.vars['gdbmi#_channel_id'] = self.vim.channel_id

    @neovim.rpc_export('launchgdb')
    def launchgdb(self, args):
        debugee = args[0]
        self.session = Session(debugee)

    @neovim.rpc_export('breakswitch')
    def breakswitch(self, args):
        (bufnr, line) = args
        for b in self.vim.buffers:
            if b.number == bufnr:
                filename = b.name
                break
        else:
            self._error("not found buffer")
            return

        self.session.do_breakswitch(filename, line)


def main(vim):
    plugin_instance = GDBMI_plugin(vim)

if __name__ == "__main__":
    import sys
    main(sys.argv[1])

