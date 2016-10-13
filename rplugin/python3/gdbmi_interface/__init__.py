import logging
import traceback
import os
import fcntl
import termios
import struct

import neovim

from .gdbmi.session import Session

def ansi(string, style):
    return '\x1b[{}m{}\x1b[0m'.format(style, string)

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
        #  output = open(term_tty, 'w')
        #  output.write('hello world\n')
        #  output.flush()
        return term_tty

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
        term_tty = self.openTerminalWindow()
        self.ouput = open(term_tty, 'w')
        self.session = Session(debugee, gdb_tty)

    @neovim.rpc_export('breakswitch', sync=False)
    def breakswitch(self, args):
        filename, line = args
        self.session.do_breakswitch(filename = filename, line = line)

    @neovim.rpc_export('exec', sync=False)
    def exec(self, args):
        filename, line = self.session.exec(args[0], args[1:])

        self.vim.command('buffer +{} {}'.format(line, filename))

    def _display(self):
        raw = fcntl.ioctl(self.output.fileno(), termios.TIOCGWINSZ, ' ' * 4)
        height, width = struct.unpack('hh', raw)

        self.output.write('\x1b[H\x1b[J') #  clear screen

        lines = []
        for m in [self._panel_locals, self._panel_console_output, self._panel_frames]:
            lines.extend(m(width))

        for l in lines:
            self.output.write(l)
        self.output.flush()

    def _panel_locals(self, width):
        lines = [ansi("─"*5+"{0:─<15}".format("variables")+"─"*(width-20), '36')]

        variables = self.session.get_locals()
        longestname = max((len(v['name']) for v in variables))
        longesttype = max((len(v['type']) for v in variables))

        for v in variables:
            lines.append(ansi("{name:<{longestname}}-{type:<{longesttype}}: {value}\n".
                              format(longestname=longestname,
                                     longesttype=longesttype,
                                     **v),
                              '1;32'))
        return lines

    def _panel_frames(self, width):
        lines = [ansi("─"*5+"{0:─<15}".format("frames")+"─"*(width-20), '36')]
        frames = self.session.get_frames()

        for v in frames:
            lines.append(ansi("[{level} from {addr} in {func} at {file}:{line}\n".
                              format(**v),
                              '1;32'))

        return lines

    def _panel_console_output(self, width)
        lines = [ansi("─"*5+"{0:─<15}".format("console_output")+"─"*(width-20), '36')]

        console_output = self.session.get_console_output()

        for o in console_output:
            lines.append(ansi(o, '1;32'))

def main(vim):
    plugin_instance = GDBMI_plugin(vim)

if __name__ == "__main__":
    import sys
    main(sys.argv[1])

