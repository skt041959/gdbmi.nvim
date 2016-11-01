import logging
import traceback
import os
import fcntl
import termios
import struct

import neovim

from .gdbmi import Session
from .hues import huestr
from .vim_signs import BPSign, PCSign

def ansi(string, style):
    return '\x1b[{}m{}\x1b[0m'.format(style, string)

def label(label_name, width):
    return ''.join([huestr('-'*5).bright_white.colorized,
                    huestr(label_name).bright_green.colorized,
                    huestr('-'*(width-5-len(label_name))).bright_white.colorized])

@neovim.plugin
class GDBMI_plugin():
    def __init__(self, vim):
        self.vim = vim

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.logger.debug('[gdbmi]plugin instance init')

        self.panels = []

        self.session = None
        self.bp_signs = {}
        self.pc_signs = {}

    def _insert_panel(self, f):
        self.panels.append(f)
        return f

    def openTerminalWindow(self):
        vim = self.vim
        vim.call('gdbmi#init#createWindow')

        for w in vim.windows:
            if w.buffer.name.startswith('term:'):
                self.gdb_window = w
                break

        term_pid = vim.vars['gdbmi#_terminal_job_pid']
        term_tty = os.readlink("/proc/{pid}/fd/0".format(pid=term_pid))
        return term_tty

    @neovim.command('GdbmiInitializePython', sync=True, nargs=0)
    def init_python(self):
        self.vim.vars['gdbmi#_python_pid'] = os.getpid()
        self.vim.vars['gdbmi#_channel_id'] = self.vim.channel_id

    @neovim.rpc_export('launchgdb', sync=False)
    def launchgdb(self, args):
        debugee = args[0]
        term_tty = self.openTerminalWindow()
        self.output = open(term_tty, 'w')
        self.session = Session(self.vim, debugee)
        self._display()

    @neovim.rpc_export('quitgdb', sync=False)
    def quitgdb(self, args):
        self.session.quit()

        current = self.vim.current.window

        self.vim.current.window = self.gdb_window
        self.command(":q")
        self.vim.current.window = current

    @neovim.rpc_export('breakswitch', sync=False)
    def breakswitch(self, args):
        filename, line = args
        bkpt_number = self.session.do_breakswitch(filename = filename, line = line)

        self.bp_signs[bkpt_number] = BPSign(self.vim, filename=filename, line=line)

    @neovim.rpc_export('exec', sync=False)
    def exec(self, args):
        def callback(filename, line):
            self.logger.debug("exec callback")
            self.vim.command('buffer +{} {}'.format(line, filename))
            self._display()

        if not self.session.do_exec(args[0], *args[1:], callback=callback):
            self.vim.err_write("exec fail\n")

    def _update_pc(self, frames):
        self.logger.debug("update pc sign")
        for s in self.pc_signs.values():
            s.hide()

        self.pc_signs.clear()

        for f in frames:
            self.pc_signs[f['level']] = PCSign(self.vim, f['fullname'], f['line'], selected=(f['level']=='0'))

    def _display(self):
        self.logger.debug("update display")
        raw = fcntl.ioctl(self.output.fileno(), termios.TIOCGWINSZ, ' ' * 4)
        height, width = struct.unpack('hh', raw)

        self.output.write('\x1b[H\x1b[J') #  clear screen

        lines = []
        if self.session.exec_state == 'ready':
            panels = ['breakpoints', 'console_output']
        else:
            panels = ['breakpoints', 'console_output', 'locals', 'frames', 'threads']
        for m in panels:
            caller = getattr(self, '_panel_'+m)
            lines.extend(caller(width))
            lines.append("\n")

        for l in lines:
            self.output.write(l)

        self.output.flush()

    def _panel_locals(self, width):
        lines = [label('variables', width)]

        variables = self.session.get_locals()
        longestname = max((len(v['name']) for v in variables))
        longesttype = max((len(v['type']) for v in variables))

        for v in variables:
            line = (huestr(v['name']).green.colorized + " "*(longestname-len(v['name'])+1) +
                    huestr(v['type']).green.colorized + " "*(longesttype-len(v['type'])) + ":" +
                    huestr(v['value']).green.colorized + "\n")
            lines.append(line)

        return lines

    def _panel_frames(self, width):
        lines = [label("frames", width)]
        frames = self.session.get_frames()

        for f in frames:
            lines.append("[{level} from {addr} in {func} at {file}:{line}\n".
                         format(level=huestr(f['level']),
                                addr=huestr(f['addr']),
                                func=huestr(f['func']),
                                file=f['file'],
                                line=f['line'],)
                         )

        self._update_pc(frames)

        return lines

    def _panel_console_output(self, width):
        lines = [label("console_output", width)]

        console_output = self.session.get_console_output()

        for o in console_output[-10:]:
            lines.append(huestr(o).white)

        return lines

    def _panel_breakpoints(self, width):
        lines = [label("breakpoints", width)]

        breakpoints = self.session.get_breakpoints()
        for number,bkpt in breakpoints.items():
            lines.append("{number}. {file}: {line}\n".format(number=number,
                                                             file=bkpt['fullname'],
                                                             line=bkpt['line']))
        return lines

    def _panel_threads(self, width):
        lines = [label("threads", width)]
        return lines


def main(vim):
    plugin_instance = GDBMI_plugin(vim)


if __name__ == "__main__":
    import sys
    main(sys.argv[1])

