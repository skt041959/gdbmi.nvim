import logging
import traceback
import os
import fcntl

import neovim

from .gdbmi.session import Session


@neovim.plugin
class GDBMI_plugin():
    def __init__(self, vim):
        self.vim = vim

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.logger.debug('[gdbmi] instance init')

        self.session = None

    def openTerminalWindow(self):
        vim = self.vim
        vim.call('gdbmi#init#createWindow')

        term_pid = vim.vars['gdbmi#_terminal_job_pid']
        term_tty = os.readlink("/proc/{}/fd/0".format(term_pid))
        output = open(term_tty, 'w')
        #  output.write('hello world\n')
        #  output.flush()
        return output

    @staticmethod
    def update_term_width(fd=1):  # defaults to the main terminal
        # first 2 shorts (4 byte) of struct winsize
        raw = fcntl.ioctl(fd, termios.TIOCGWINSZ, ' ' * 4)
        height, width = struct.unpack('hh', raw)
        Dashboard.term_width = int(width)

    @neovim.command('GdbmiInitializePython', sync=True, nargs=0)
    def init_python(self):
        self.vim.vars['gdbmi#_python_pid'] = os.getpid()
        self.vim.vars['gdbmi#_channel_id'] = self.vim.channel_id

        #  fifo_fd = os.open("/home/skt/tmp/nvim_fifo", os.O_NONBLOCK | os.O_WRONLY)
        #  fcntl.fcntl(fifo_fd, fcntl.F_SETFL, 0)
        #  fifo = os.fdopen(fifo_fd, 'w')
        #  fifo.write(str(os.getpid())+'\n')
        #  fifo.flush()

    @neovim.rpc_export('launchgdb', sync=False)
    def launchgdb(self, args):
        debugee = args[0]
        output = self.openTerminalWindow()
        self.session = Session(debugee, output)

    @neovim.rpc_export('breakswitch', sync=False)
    def breakswitch(self, args):
        filename, line = args
        self.session.do_breakswitch(filename = filename, line = line)


def main(vim):
    plugin_instance = GDBMI_plugin(vim)

if __name__ == "__main__":
    import sys
    main(sys.argv[1])

