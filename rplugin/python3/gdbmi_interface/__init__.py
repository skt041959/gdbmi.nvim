import os
import functools
import tempfile

import pynvim

from gdbmi_interface.gdbmi import Session
from gdbmi_interface.ui import ui


@pynvim.plugin
class GDBMI_plugin():

    def __init__(self, vim):

        self.vim = vim
        ui.setVim(vim)

        self.session = None

    @pynvim.function('_gdbmi_start', sync=True)
    def gdbmi_start(self, args):
        self.vim.vars['gdbmi#_channel_id'] = self.vim.channel_id

        master, slave = os.openpty()
        self.pty_master = master
        slave_path = os.ttyname(slave)

        self.session = Session(self.pty_master, ui)

        return slave_path

    @pynvim.rpc_export('breaktoggle', sync=True)
    def breakswitch(self, args):
        filename, line = args
        bp_id = self.session.breakpoints_status(filename, line)

        if bp_id:
            return "delete {}".format(bp_id)
        else:
            return "break {}:{}".format(filename, line)


    @pynvim.rpc_export('exec', sync=False)
    def exec(self, args):
        def callback(**kwargs):
            frame = kwargs.pop("frame", None)
            if frame is not None:
                filename = frame.get('fullname', None)
                if filename:
                    line = frame['line']
                    self.debug("exec callback")
                    self.vim.command('buffer +{} {}'.format(line, filename))

            error = kwargs.pop("error", None)
            if error is not None:
                msg = error['msg']
                self.vim.err_write(msg + '\n')

        if args[0] in ('run', 'next', 'step', 'continue', 'finish',
                       'next-instruction', 'step-instruction'):
            self.session.do_exec(args[0], *args[1:],
                                 callback=functools.partial(self.vim.async_call,  fn=callback))

        if args[0] is 'interrupt':
            self.session.inferior_interrupt()

        if args[0] is 'runtocursor':
            filename, line = args
            self.session.do_breakinsert(filename = filename, line = line, temp=True)
            self.session.do_exec('continue',
                                 callback=functools.partial(self.vim.async_call,  fn=callback))


def main(vim):
    plugin_instance = GDBMI_plugin(vim)

    print(plugin_instance.gdbmi_start(None))

    plugin_instance.session.reader.join()


if __name__ == "__main__":
    import sys
    main(sys.argv[1])

