
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
            self.vim.vars['gdbmi_channel_id'] = self.vim.channel_id
            self.rplugin = GDBMI_rplugin(vim)

        @vim.function('_gdbmi_start', sync=True)
        def gdbmi_start(self, args):
            self.rplugin.start(args)

        @vim.rpc_export('gdbmi_getslave', sync=True)
        def gdbmi_getslave(self, args):
            return self.rplugin.getSlave(args)

        @vim.rpc_export('gdbmi_breaktoggle', sync=True)
        def breakswitch(self, args):
            return self.rplugin.breakswitch(args)

        @vim.rpc_export('gdbmi_exec', sync=False)
        def exec(self, args):
            self.rplugin.exec(args)

        @vim.rpc_export('gdbmi_display', sync=False)
        def display(self, args):
            self.rplugin.display(args)

        @vim.rpc_export('gdbmi_stop', sync=False)
        def stop(self, args):
            self.rplugin.stop(args)

elif find_spec('yarp'):

    gdbmi = GDBMI_rplugin(vim)

    def _gdbmi_start(args):
        return gdbmi.start(args)

    def gdbmi_breaktoggle(args):
        return gdbmi.breakswitch(args)

    def gdbmi_exec(args):
        gdbmi.exec(args)

    def gdbmi_display(args):
        gdbmi.display(args)

    def gdbmi_stop(args):
        return gdbmi.stop(args)

