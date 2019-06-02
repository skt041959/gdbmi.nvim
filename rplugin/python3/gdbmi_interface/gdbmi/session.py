import os
import fcntl
import asyncio

from subprocess import Popen, PIPE

from gdbmi_interface.log import getLogger, log_exceptions
from gdbmi_interface.gdbmi.parse import GDBOutputParse, ParseError
from gdbmi_interface.gdbmi.parse import ResultRecord, AsyncRecord, StreamRecord


logger = getLogger(__name__)


class Session(object):
    debug, info, warn = (logger.debug, logger.info, logger.warn,)

    def __init__(self, name, gdbmi_interface_fd, slave_path, ui):
        self.name = name
        self.slave_path = slave_path
        self.gdbmi_interface_fd = gdbmi_interface_fd
        self.ui = ui

        self.thread_groups = {}
        self.breakpoints = {}

        self.commands = {}
        self._callbacks = {}
        self._display_exprs = {}

        self.parser = GDBOutputParse()
        self.token = 0
        self.handlers = {'ResultRecord'   : self._handle_result,
                         'AsyncRecord'    : self._handle_async,
                         'StreamRecord'   : self._handle_stream,
                         }

        self.gdbmi = os.fdopen(self.gdbmi_interface_fd, mode='wb+', buffering=0)
        loop = asyncio.get_event_loop()
        loop.add_reader(self.gdbmi_interface_fd, self.read_task)

        self.debug("Session launched")

    def _launch_gdb(self, debuggee, gdb):
        p = Popen(bufsize = 0,
                  args = [gdb,
                          '--return-child-result',
                          '--quiet', # inhibit dumping info at start-up
                          '--nx', # inhibit window interface
                          '--nw', # ignore .gdbinit
                          '--interpreter=mi2', # use GDB/MI v2
                          #'--write', # to-do: allow to modify executable/cores?
                          debuggee,
                          ],
                  stdin = PIPE,
                  stdout = PIPE,
                  close_fds = True)
        fl = fcntl.fcntl(p.stdout, fcntl.F_GETFL)
        fcntl.fcntl(p.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        return p

    def _send(self, cmd, **kwargs):
        self.token += 1
        token = "%04d" % self.token
        self.commands[token] = {'cmd': cmd}
        self.commands[token].update(kwargs)

        buf = token + cmd + "\n"
        #  self.process.stdin.write(buf.encode('utf8'))
        self.gdbmi.write(buf.encode('utf8'))

        return token

    @log_exceptions(logger)
    def read_task(self, *args):
        line = self.gdbmi.readline()
        if not line:
            raise GDBStopped
        self._handle(line)

    def _handle(self, line):
        def _ignore(token, obj):
            self.warn(["IGN:", token, obj])
            return False

        self.debug('\n'+repr(line))
        try:
            token, obj = self.parser.parse(line.decode('utf8').rstrip('\r\n') + '\n')
        except ParseError as e:
            raise e
        else:
            if obj is None or obj is self.parser.GDB_PROMPT:
                return
            self.debug("obj {}".format(obj.What))
            self.handlers.get(obj.What, _ignore)(token, obj)
            event = self.commands.get(token, {}).get('waiting', None)
            if event is not None:
                event.set()

    def _handle_result(self, token, obj):
        self.debug("handle result")
        if token is None:
            return

        command = self.commands.get(token, None)
        if command is None:
            self.error("Unexpected feed back token")
            return

        command['state'] = obj.What
        command['result'] = obj
        if "event" in command:
            command["event"].set()

    def _handle_async_notify(self, token, obj, kwargs):
        if obj.name == "thread-group-added":
            self._add_thread_group(obj.results)
            return True

        elif obj.name == "thread-group-started":
            tg = self.thread_groups[obj.results['id']]
            tg['pid'] = obj.results['pid']
            return True

        elif obj.name == "thread-groups-exited":
            self._del_thread_group(obj.results['id'])
            self.ui.del_cursor(obj.results['id'])
            return True

        elif obj.name == "thread-created":
            tg = self.thread_groups[obj.results['group-id']]
            tg['threads'].add(obj.results['id'])
            return True

        elif obj.name == "thread-selected":
            self.ui.jump_frame(obj.results['frame'])

        elif obj.name == "library-loaded":
            tg = self.thread_groups[obj.results['thread-group']]
            tg['library'][obj.results['id']] = obj.results
            return True

        elif obj.name == "breakpoint-modified":
            self._update_breakpoint(obj.results['bkpt'])
            return True

        elif obj.name == "breakpoint-created":
            self._update_breakpoint(obj.results['bkpt'], new=True)
            return True

        elif obj.name == "breakpoint-deleted":
            self._update_breakpoint(None, number=obj.results['id'])

    def _handle_async_exe(self, token, obj, kwargs):
        if obj.name == 'running':
            self.exec_state = 'running'
            return True

        elif obj.name == 'stopped':
            self.exec_state = 'stopped'
            frame = obj.results.get('frame', None)
            if frame is None:
                return True
            callback = self.commands.get(token, {}).get('exec_callback', None)
            if callback:
                self.debug("calling exec callback")
                callback(frame)
            self.ui.jump_frame(frame)
            self._query_display(frame)
            return True

    def _handle_async(self, token, obj, **kwargs):
        self.debug("handle async")
        if obj.async_class == "NOTIFY_CLASS":
            return self._handle_async_notify(token, obj, kwargs)

        elif obj.async_class == 'EXEC_CLASS':
            return self._handle_async_exe(token, obj, kwargs)

        return False

    def _handle_stream(self, token, obj):
        #  self.debug(repr(obj))
        return True

    def _add_thread_group(self, info, group_id = None):
        if group_id is None:
            group_id = info['id']
        tg = {
            'id': group_id,
            "pid": None,
            "threads": set(),
            "library": {},
        }
        self.thread_groups[group_id] = tg
        self.info(tg)

    def _del_thread_group(self, group_id):
        try:
            tg = self.thread_groups.pop(group_id)
        except KeyError:
            return False

        self.info(tg)

    def _callback(self, target, **kwds):
        for to_call in self._callbacks.get(target, []):
            if ('filter' in to_call) and (not to_call['filter'](kwds)):
                continue
            tmp_kwds = dict(kwds)
            tmp_kwds.update(to_call)
            to_call['proc'](tmp_kwds)

    def _update_breakpoint(self, info, number = None, new=False):
        if number is None:
            number = info['number']
        self.debug(info)

        if info is None:
            self.breakpoints.pop(number)
            self.ui.del_breakpoint(int(number))
            return

        if number in self.breakpoints:
            self.breakpoints[number].update(info)
        else:
            self.breakpoints[number] = dict(info)

        if new and 'fullname' in info:
            self.ui.set_breakpoint(int(number), info['fullname'], info['line'])

    def breakpoints_status(self, filename, line):
        for number, bkpt in self.breakpoints.items():
            if bkpt['type'] == 'breakpoint' and int(bkpt['line']) == int(line) and bkpt['fullname'] == filename:
                return number
        else:
            return 0

    def wait_for(self, token):
        self.debug("waiting for {}".format(token))
        return self.commands[token]['waiting'].wait()

    def do_breakinsert(self, **kwargs):
        def get_bkptnumber(obj):
            nonlocal bkpt_number
            bkpt_number = obj.results['bkpt']['number']

        args = []
        filename = kwargs.pop('filename', None)
        line = kwargs.pop('line', None)
        function = kwargs.pop('function', None)

        if kwargs.pop('temp', False):
            args.append('-t')

        if filename and line:
            l = filename + ':' + str(line)
        elif function:
            l = kwargs.pop('function')
        else:
            raise Exception(" Cannot insert break at filanem:{} line:{} function:{}"
                            .format(filename, line, function))
        args.append(l)

        self.debug("breakswitch at {}".format(l))

        bkpt_number = None
        token = self._send("-break-insert " + " ".join(args),
                           waiting=asyncio.Event(), result_callback = get_bkptnumber)
        self.wait_for(token)

        return bkpt_number

    def do_breakdelete(self, **kwargs):
        filename = kwargs['filename']
        line = kwargs['line']

        for number, bkpt in self.breakpoints.items():
            if bkpt['fullname'] == filename and bkpt['line'] == line:
                break

        token = self._send(f'-break-delete {number}', waiting=asyncio.Event())
        self.wait_for(token)

        self.breakpoints.pop(number)

    def modify_breakpoint(self, bkpt, bkpt_new):
        condition = bkpt_new.pop('cond', None)
        ignore_count = bkpt_new.pop('ignore', None)
        #  enable_count = bkpt_new.pop('enable', None)
        enabled = bkpt_new.pop('enabled', None)

        if condition:
            token = self._send(' '.join(['-break-condition', bkpt['number'], condition]))

        if ignore_count:
            token = self._send(' '.join(['-break-after', bkpt['number'], ignore_count]))

        if enabled != bkpt['enabled']:
            if enabled == 'y':
                token = self._send('-break-enable '+bkpt['number'])
            elif enabled == 'n':
                token = self._send('-break-disable '+bkpt['number'])

    def do_exec(self, cmd, *args, callback=None):
        if cmd in ('run', 'next', 'step', 'continue', 'finish',
                       'next-instruction', 'step-instruction'):
            token = self._send("-exec-" + cmd + " " + " ".join(args), exec_callback=callback)
            return token

    def inferior_interrupt(self):
        self.process.send_signal(2)
        return True

    def inferior_stdin(self, content):
        if not content.endswith("\n"):
            content += "\n"
        self.debuggee_file.write(content)

    def get_console_output(self):
        return self.console_output

    def get_debugee_output(self):
        return self.debugee_output

    def get_breakpoints(self, **kwargs):
        if 'filename' in kwargs:
            filename = kwargs.pop('filename')
            kwargs['fullname'] = filename

        if 'line' in kwargs:
            kwargs['line'] = str(kwargs['line'])

        breakpoints = list(filter(lambda x: all((x[k] == v for k,v in kwargs.items())),
                                  self.breakpoints.values()))

        return breakpoints

    def add_display(self, expr):
        self._display_exprs[expr] = []

    def _query_display(self, frame):
        self._query_display_expr(frame)

    async def _query_display_expr(self, frame):
        for expr, values in self._display_exprs.keys():
            result_event = asyncio.Event()
            #  self._send('-data-evaluate-expression {}'.format(expr), lambda obj: self._display_exprs[expr].append(obj['value']))
            token = self._send(f'-data-evaluate-expression {expr}', event=result_event)
            await result_event.wait()
            obj = self.commands[token]['result']
            values.setdefault(frame['addr'], []).append(obj['value'])

    def stop(self):
        loop = asyncio.get_event_loop()
        loop.remove_reader(self.gdbmi_interface_fd)


class GDBStopped(Exception):
    pass


if __name__ == "__main__":
    master, slave = os.openpty()
    pty_master = master
    slave_path = os.ttyname(slave)

    session = Session(pty_master)
    session.conn.join()

