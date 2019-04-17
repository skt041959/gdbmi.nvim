
from importlib.util import find_spec

from gdbmi_interface.rplugin import GDBMI_rplugin

if find_spec('yarp'):
    import vim
elif find_spec('pynvim'):
    import pynvim
    vim = pynvim
else:
    import neovim
    vim = neovim

if hasattr(vim, 'plugin'):

    @vim.plugin
    class plugin():

        def __init__(self, vim):
            self.vim = vim
            self.vim.vars['gdbmi#_channel_id'] = self.vim.channel_id
            self.rplugin = GDBMI_rplugin(vim)

        @vim.function('_gdbmi_start', sync=True)
        def gdbmi_start(self, args):
            return self.rplugin.gdbmi_start(args)

        @vim.rpc_export('gdbmi_breaktoggle', sync=True)
        def breakswitch(self, args):
            return self.rplugin.breakswitch(args)

        @vim.rpc_export('gdbmi_exec', sync=False)
        def exec(self, args):
            self.rplugin.exec(args)

        @vim.rpc_export('gdbmi_display', sync=False)
        def display(self, args):
            self.rplugin.display(args)

if find_spec('yarp'):

    gdbmi = GDBMI_rplugin(vim)

    def _gdbmi_start(args):
        gdbmi.gdbmi_start(args)

    def breaktoggle(args):
        return gdbmi.breakswitch(args)

    def gdbmi_exec(args):
        gdbmi.exec(args)
