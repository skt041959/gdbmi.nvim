import os
import functools

import pynvim

from gdbmi_interface.gdbmi import Session


@pynvim.plugin
class GDBMI_plugin():

    def __init__(self, vim):

        self.vim = vim

        self.panels = []

        self.session = None
        self.bp_signs = {}
        self.pc_signs = {}

    @pynvim.function('_gdbmi_start', sync=True)
    def gdbmi_start(self, args):
        master, slave = os.openpty()
        self.pty_master = master
        slave_path = os.ttyname(slave)

        self.session = Session(self.pty_master, None) # FIXME

        return slave_path

    @pynvim.rpc_export('breakswitch', sync=False)
    def breakswitch(self, args):
        filename, line = args
        if (filename, line) in self.bp_signs:
            self.session.do_breakdelete(filename=filename, line=line)
            bps = self.bp_signs.pop((filename, line))
            bps.hide()
        else:
            bkpt_number = self.session.do_breakinsert(filename = filename, line = line)

            self.bp_signs[(filename, line)] = BPSign(self.vim, filename=filename, line=line)

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

    def _update_pc(self, frames):
        self.debug("update pc sign")

        old_pc_signs = self.pc_signs
        self.pc_signs = {}

        for f in frames:
            filename = f.get('fullname', None)
            if filename:
                key = (filename, f['line'], (f['level']==0))
                s = old_pc_signs.pop(key, None)
                if s:
                    self.pc_signs[key] = s
                else:
                    self.pc_signs[key] = PCSign(self.vim, *key)

        for s in old_pc_signs.values():
            s.hide()


def main(vim):
    plugin_instance = GDBMI_plugin(vim)


if __name__ == "__main__":
    import sys
    main(sys.argv[1])

