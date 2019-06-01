import os
import functools

from gdbmi_interface.gdbmi import Session
from gdbmi_interface.ui import ui

class GDBMI_rplugin():
    def __init__(self, vim):
        self.vim = vim
        ui.setVim(vim)

        self.session = None

    def gdbmi_start(self, args):
        master, slave = os.openpty()
        self.pty_master = master
        slave_path = os.ttyname(slave)

        if self.session is None:
            self.session = Session(self.pty_master, ui, name=args[0])
            return slave_path
        else:
            ui.error("There is already a gdb session running. Maybe you want to add another gdb inferior.")
            return ""

    def gdbmi_stop(self, args):
        self.session.stop()
        self.session = None

    def breakswitch(self, args):
        filename, line = args
        bp_id = self.session.breakpoints_status(filename, line)

        if bp_id:
            return "delete {}".format(bp_id)
        else:
            return "break {}:{}".format(filename, line)

    def display(self, args):
        expr = args[0]
        self.session.add_display(expr)

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

