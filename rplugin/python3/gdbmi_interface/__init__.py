import logging
import traceback
import os
import fcntl
import termios
import struct

import neovim

from .gdbmi.session import Session
from .hues import huestr

def ansi(string, style):
    return '\x1b[{}m{}\x1b[0m'.format(style, string)

def label(label_name, width):
    return ''.join([huestr('-'*5).bright_white,
                    huestr(label_name).bright_green,
                    huestr('-'*(width-5-len(label_name))).bright_white])

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
        self.session = Session(self.vim, debugee)

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
        lines = [label('variables')]

        variables = self.session.get_locals()
        longestname = max((len(v['name']) for v in variables))
        longesttype = max((len(v['type']) for v in variables))

        for v in variables:
            lines.append("{name:<{longestname}}-{type:<{longesttype}}: {value}\n".
                         format(longestname=longestname,
                                longesttype=longesttype,
                                name=huestr(v.name).white,
                                type=huestr(v.type).green,)
                         )
        return lines

    def _panel_frames(self, width):
        lines = [label("frames")]
        frames = self.session.get_frames()

        for f in frames:
            lines.append(ansi("[{level} from {addr} in {func} at {file}:{line}\n".
                              format(**v),
                              '1;32'))
            lines.append("[{level} from {addr} in {func} at {file}:{line}\n".
                         format(level=huestr(f.level),
                                addr=huestr(f.addr),
                                file=f.file,
                                line=f.line,)
                         )

        return lines

    def _panel_console_output(self, width):
        lines = [label("console_output")]

        console_output = self.session.get_console_output()

        for o in console_output:
            lines.append(huestr(o).white)

def main(vim):
    plugin_instance = GDBMI_plugin(vim)

if __name__ == "__main__":
    import sys
    main(sys.argv[1])

