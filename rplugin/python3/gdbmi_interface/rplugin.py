import os
import functools

from gdbmi_interface.gdbmi import Session
from gdbmi_interface.ui import ui

class GDBMI_rplugin():
    def __init__(self, vim):
        self.vim = vim
        ui.setVim(vim)

        self.sessions = {}
        self.master = None
        self.slave_path = ""

    def start(self, args):
        name = args[0]
        master, slave = os.openpty()
        slave_path = os.ttyname(slave)
        self.sessions[name] = Session(name, master, slave_path, ui)
        return slave_path

    def stop(self, args):
        name = args[0]
        self.sessions[name]['session'].stop()
        del self.sessions[name]

    def breakswitch(self, args):
        session_name, filename, line = args
        session = self.sessions[session_name]
        bp_id = session.breakpoints_status(filename, line)

        if bp_id:
            return f"delete { bp_id }"
        else:
            return f"break { filename }:{ line }"

    def display(self, args):
        session_name, expr = args
        self.sessions[session_name].add_display(expr)

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

