import logging
import traceback
import os
import fcntl
import termios
import struct
import json
import functools

import neovim

from .gdbmi import Session
from .hues import huestr
from .vim_signs import BPSign, PCSign

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def ansi(string, style):
    return '\x1b[{}m{}\x1b[0m'.format(style, string)


def label(label_name, width):
    return ''.join([huestr('-'*5).bright_white.colorized,
                    huestr(label_name).bright_yellow.colorized,
                    huestr('-'*(width-5-len(label_name))).bright_white.colorized])


class Colorize():
    def __init__(self, obj, name, **options):
        self.obj = obj
        self.name = name
        self.colorize = getattr(self, 'colorize_'+self.name)
        self.option = options
        self.bright = self.option.get('bright', False)

    def __getitem__(self, key):
        value = self.obj[key]
        if isinstance(value, (str, bytes)):
            return self.colorize(value)
        else:
            return Colorize(value, name=self.name, **self.option)

    def colorize_thread(self, value):
        if self.bright:
            return huestr(value).bright_green.colorized
        else:
            return huestr(value).green.colorized

    def colorize_frame(self, value):
        if self.bright:
            return huestr(value).bright_green.colorized
        else:
            return huestr(value).green.colorized


@neovim.plugin
class GDBMI_plugin():
    max_debugee_display = 10

    def __init__(self, vim):
        def init():
            self.vim.vars['gdbmi#_python_pid'] = os.getpid()
            self.vim.vars['gdbmi#_channel_id'] = self.vim.channel_id

        self.debug, self.info, self.warn = (logger.debug, logger.info, logger.warn,)

        self.vim = vim
        self.vim.async_call(init)

        self.panels = []

        self.session = None
        self.bp_signs = {}
        self.pc_signs = {}

    def openTerminalWindow(self):
        vim = self.vim
        w = self.vim.current.window

        self.vim.command(":only | vnew | wincmd L")
        self.gdb_window = self.vim.current.window

        self.vim.command(":10new")
        self.debugee_output_buf = self.vim.current.buffer
        self.debugee_output_buf.name = '[output]'
        self.debugee_output_buf.options['swapfile'] = False
        self.debugee_output_buf.options['buftype'] = "nofile"

        self.vim.current.window = self.gdb_window
        self.vim.command(":e term://zsh")
        term_pid = self.vim.current.buffer.vars["terminal_job_pid"]
        term_id = self.vim.current.buffer.vars["terminal_job_id"]

        self.vim.current.window = w

        term_tty = os.readlink("/proc/{pid}/fd/0".format(pid=term_pid))
        return term_tty

    def wrap_debugee_output(self, output):
        def update_output_buf(index, lines):
            self.debugee_output_buf[index] = None
            self.debugee_output_buf.append(lines)

        try:
            debugee_output = output.decode('utf8').splitlines()
            n = len(debugee_output) - len(self.debugee_output)
        except UnicodeError as e:
            self.vim.err_write(e)
            self.vim.err_write("\n")
        else:
            self.vim.async_call(update_output_buf,
                                index = len(self.debugee_output),
                                lines = debugee_output[-n:])
            self.debugee_output = debugee_output

    #  @neovim.function('GdbmiInitializePython')
    @neovim.command('GdbmiInitializePython', sync=True, nargs=0)
    def init_python(self):
        pass

    @neovim.rpc_export('launchgdb', sync=False)
    def launchgdb(self, args):
        debugee = args[0]
        term_tty = self.openTerminalWindow()

        self.output = open(term_tty, 'w')
        self.session = Session(debugee)

        self.session.wrap_child_inout(callback=self.wrap_debugee_output)
        self.debugee_output = ''

        self._display()

    @neovim.rpc_export('quitgdb', sync=False)
    def quitgdb(self, args):
        self.session.quit()

        current = self.vim.current.window

        self.vim.current.window = self.gdb_window
        self.command(":q!")
        self.vim.current.window = current

    @neovim.rpc_export('breakswitch', sync=False)
    def breakswitch(self, args):
        filename, line = args
        if (filename, line) in self.bp_signs:
            self.session.do_breakdelete(filename=filename, line=line)
            bps = self.bp_signs.pop((filename, line))
            bps.hide()
        else:
            bkpt_number = self.session.do_breakinsert(filename = filename, line = line)

            self.bp_signs[(filename, line)] = BPSign(self.vim, filename=filename, line=line)

    @neovim.rpc_export('bkpt_property', sync=False)
    def bkpt_property(self, args):
        filename, line = args
        bkpt = self.session.get_breakpoints(filename=filename, line=line)
        self.debug(repr(bkpt))
        bkpt = bkpt[0] # FIXME: if get multiple breakpoint
        bkpt_json = []
        bkpt_json.extend(json.dumps(bkpt, indent=4).split('\n'))

        self.vim.command(":new")
        self.vim.command(":nmap <buffer> q <Plug>GDBBreakModify")
        buf = self.vim.current.buffer
        buf.options["swapfile"] = False
        buf.options["buftype"] = "nofile"
        #  buf.options["syntax"] = "json"
        self.vim.command(":setlocal syntax=json")
        buf.name = "[bkpt_property]"
        buf[0] = "# press q to apply modify"
        buf.append("# cond: make a condition break point, enabled: toggle the break point state")
        src = self.vim.new_highlight_source()
        buf.add_highlight("Comment", 0, src_id=src)
        buf.add_highlight("Comment", 1, src_id=src)

        buf.append(bkpt_json)

        self.bkpt_displayd = (bkpt, buf)

    @neovim.rpc_export('bkpt_modify', sync=False)
    def bkpt_moodify(self, args):
        bkpt, buf = self.bkpt_displayd
        buf_content = ''.join([e for e in buf if not e.startswith("#")])

        self.vim.command(":q!")
        self.session.modify_breakpoint(bkpt, json.loads(buf_content))

    @neovim.rpc_export('exec', sync=False)
    def exec(self, args):
        def callback(filename, line):
            self.debug("exec callback")
            self.vim.command('buffer +{} {}'.format(line, filename))
            self._display()

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
            key = (f['fullname'], f['line'], (f['level']==0))
            s = old_pc_signs.pop(key, None)
            if s:
                self.pc_signs[key] = s
            else:
                self.pc_signs[key] = PCSign(self.vim, *key)

        for s in old_pc_signs.values():
            s.hide()

    def _display(self):
        self.debug("update display")
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
            lines.append("[{0[level]}] from {0[addr]} in {0[func]} at {0[file]}:{0[line]}"
                         "\n"
                         .format(Colorize(f, name='frame')))

        self._update_pc(frames)

        return lines

    def _panel_console_output(self, width, old_console_output=[]):
        lines = [label("console_output", width)]

        console_output = self.session.get_console_output()
        n = len(console_output) - len(old_console_output)

        for o in console_output[-10:-n]:
            lines.append(huestr(o).white.colorized)

        for o in console_output[-n:]:
            lines.append(huestr(o).green.colorized)
            old_console_output.append(o)

        return lines

    def _panel_breakpoints(self, width):
        lines = [label("breakpoints", width)]

        breakpoints = self.session.get_breakpoints()
        for bkpt in breakpoints:
            lines.append("{number}. {fullname}: {line}\n".format_map(bkpt))
        return lines

    def _panel_threads(self, width):
        lines = [label("threads", width)]

        results = self.session.get_threads()
        threads = results['threads']
        for th in threads:
            self.debug(repr(th))
            lines.append("[{0[id]}] {0[target-id]}"
                         " from {0[frame][addr]} in {0[frame][func]}"
                         " at {0[frame][fullname]}:{0[frame][line]}"
                         "\n"
                         .format(Colorize(th, name='thread', bright=True)))
        return lines


def main(vim):
    plugin_instance = GDBMI_plugin(vim)


if __name__ == "__main__":
    import sys
    main(sys.argv[1])

