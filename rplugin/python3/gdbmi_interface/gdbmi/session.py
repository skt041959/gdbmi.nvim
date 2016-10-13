#!/usr/bin/python

import os
import pty
import sys
import fcntl
import select
import logging
import functools

from collections import deque
from subprocess import Popen, PIPE

from greenlet import greenlet

from .parse import GDBOutputParse, ParseError
from .parse import ResultRecord, AsyncRecord, StreamRecord

class Handled(object): pass


class ErrorArgumentsException(Exception): pass


def exception(logger):
    """
    A decorator that wraps the passed in function and logs
    exceptions should one occur

    @param logger: The logging object
    """

    def decorator(func):

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                # log the exception
                err = "There was an exception in  "
                err += func.__name__
                logger.exception(err)

            # re-raise the exception
            raise
        return wrapper
    return decorator


class Session(object):
    def __init__(self, debuggee, gdb="gdb"):
        """
        >>> p = Session("test/hello")
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.buf = ""
        self.is_attached = False

        self.thread_groups = {}
        self.breakpoints = {}

        self.commands = {}
        self._callbacks = {}
        self._hijacked = {}

        self.exec_state = 'ready'

        self.debuggee = debuggee

        self.process = self._launch_gdb(debuggee, gdb)

        self.token = 0

        self.sender = greenlet(self._send)
        self.reader = greenlet(self._read)

        self.waiting_cmd = deque()

        self.console_output = []
        if self.reader.switch(self._handle, 0):
            self.sendable = True

        self.logger.debug("session: {} gdb: {}".format(debuggee, gdb))

        master_fd = self.inferior_tty_set()
        self.debuggee_file = open(master_fd, 'w')

        self._display()

    def _launch_gdb(self, debuggee, gdb):
        p = Popen(bufsize = 0,
                  args = [gdb,
                          '--return-child-result',
                          '--quiet', # inhibit dumping info at start-up
                          '--nx', # inhibit window interface
                          '--nw', # ignore .gdbinit
                          '--interpreter=mi2', # use GDB/MI v2
                          #'--write', # to-do: allow to modify executable/cores?
                          self.debuggee,
                          ],
                  stdin = PIPE,
                  stdout = PIPE,
                  close_fds = True)
        fl = fcntl.fcntl(p.stdout, fcntl.F_GETFL)
        fcntl.fcntl(p.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        return p

    def _send(self, cmd, handler):
        if self.sendable:
            self.token += 1
            token = "%04d" % self.token
            buf = token + cmd + "\n"
            self.process.stdin.write(buf.encode('utf8'))

            self.logger.debug("SENT[{0}]: {1}".format(token, cmd))
            self.commands[token] = {'cmd': cmd, 'handler': handler}
            return token
        else:
            return None

    def _read(self, handler, blocking = 0):
        p = self.process
        parser = GDBOutputParse()
        while 1:
            rd = select.select([p.stdout], [], [], blocking)[0]
            if p.stdout in rd:
                buf = p.stdout.readline().decode('utf8')
                self.logger.debug('RAW: ' + buf)
                try:
                    token, result = parser.parse(buf)
                except ParseError as e:
                    #  self.vim.err_write("[gdbmi]: gdb output parse error\n")
                    raise e
                else:
                    if result is parser.GDB_PROMPT:
                        token = greenlet.getcurrent().parent.switch(True)
                        if token:
                            handler = self.commands[token]['handler']
                        else:
                            handler = self._handle
                        self.logger.debug("switch in {}".format(greenlet.getcurrent()))
                        continue

                    #  import ipdb
                    #  ipdb.set_trace()
                    if handler(token, result):
                        pass
                    else:
                        self.logger.error('=======' + repr(result))
                    blocking = 0

    def _handle(self, token, obj):
        def _ignore(token, obj):
            self.logger.warn(["IGN:", token, obj])
            return False

        handler = {'ResultRecord'   : self._handle_result,
                   'AsyncRecord'    : self._handle_async,
                   'StreamRecord'   : self._handle_stream,
                   }.get(obj.What, _ignore)

        return handler(token, obj)

    def _handle_result(self, token, obj):
        #  self.logger.debug(repr(obj))
        handled = False
        if obj.result_class == "done" or obj.result_class == "running":
            self.commands[token]['state'] = obj.What
            # lookup handler for the token
            #  if self.commands[token]['handler']:
            #      handled = self.commands[token]['handler'](token, obj)

            if 'bkpt' in obj.results:
                self._update_breakpoint(obj.results['bkpt'])
            handled = True
        return handled

    def _handle_async(self, token, obj, **kwargs):
        #  self.logger.debug(repr(obj))
        if obj.async_class == "NOTIFY_CLASS":
            if obj.name == "thread-group-added":
                tg = self._add_thread_group(obj.results)
                self.logger.info(tg)
                return True

            if obj.name == "thread-group-started":
                tg = self.thread_groups[obj.results['id']]
                tg['pid'] = obj.results['pid']
                self.logger.info(tg)
                return True

            if obj.name == "thread-created":
                tg = self.thread_groups[obj.results['group-id']]
                tg['threads'].add(obj.results['id'])
                self.logger.info(tg)
                return True

            if obj.name == "library-loaded":
                tg = self.thread_groups[obj.results['thread-group']]
                tg['dl'][obj.results['id']] = obj.results
                self.logger.info(tg)
                return True

            if obj.name == "breakpoint-modified":
                self._update_breakpoint(obj.results['bkpt'])
                return True

        if obj.async_class == 'EXEC_CLASS':
            if obj.name == 'running':
                self.exec_state = 'running'
                return True

            elif obj.name == 'stopped':
                self.exec_state = 'stopped'
                return True

        return False

    def _handle_stream(self, token, obj):
        #  self.logger.debug(repr(obj))
        if obj.stream_class == 'CONSOLE_OUTPUT':
            self.console_output.append(obj.output)
        return True

    def _add_thread_group(self, info, group_id = None):
        if group_id is None:
            group_id = info['id']
        tg = {
            'id': group_id,
            "pid": None,
            "threads": set(),
            "dl": {},
        }
        self.thread_groups[group_id] = tg
        self.logger.info(tg)

    def add_callback(self, target, proc, filter = None, *kwds):
        to_add = {
            'proc': proc,
            'kwds': kwds,
            'filter': filter,
        }
        self._callbacks.setdefault(target, []).append(to_add)

    def _callback(self, target, **kwds):
        for to_call in self._callbacks.get(target, []):
            if ('filter' in to_call) and (not to_call['filter'](kwds)):
                continue
            tmp_kwds = dict(kwds)
            tmp_kwds.update(to_call)
            to_call['proc'](tmp_kwds)

    def _update_breakpoint(self, info, number = None):
        if number is None:
            number = info['number']
        if number in self.breakpoints:
            self.breakpoints[number].update(info)
        else:
            self.breakpoints[number] = dict(info)

        self.logger.info(['updated BREAKPOINT', self.breakpoints[number]])
        self._callback('bkpt')

    def wait_for(self, stop_token = None):
        for token, obj in self.read(1):
            if token == stop_token:
                return True
        return False

    def inferior_tty_set(self):
        pid = os.getpid()
        (master, slave) = os.openpty()
        slave_node = "/proc/{0}/fd/{1}".format(pid, slave)
        token = self._send("-inferior-tty-set " + slave_node, self._handle)
        self.reader.switch(token)
        self.logger.debug("switch in {}".format(greenlet.getcurrent()))

        return "/proc/{0}/fd/{1}".format(pid, master)

    def do_breakswitch(self, **kwargs):
        filename = kwargs.pop('filename', None)
        line = kwargs.pop('line', None)
        if filename and line:
            l = filename + ':' + str(line)
        else:
            l = kwargs.pop('function')

        self.logger.debug("breakswitch at {}".format(l))

        token = self._send("-break-insert " + l, self._handle)

        self.reader.parent = greenlet.getcurrent()
        self.reader.switch(token)
        self.logger.debug("switch in {}".format(greenlet.getcurrent()))

        return token

    def _filter(self, container, what, **kwargs):

        def f(token, obj):
            #  self.logger.debug(repr(obj))
            if obj.What == what:
                for k,v in kwargs.items():
                    if getattr(obj, k, None) != v:
                        break
                else:
                    container.append(obj)
                    return True
            return self._handle(token, obj)

        return f

    def exec(self, cmd, args=None):
        results = []

        if cmd in ('run', 'next', 'step', 'continue', 'finish',
                       'next-instruction', 'step-instruction'):
            token = self._send("-exec-" + cmd + " " + " ".join(args),
                               self._filter(results, 'AsyncRecord', async_class='EXEC_CLASS'))

            if token is None:
                return

            self.reader.parent = greenlet.getcurrent()
            self.reader.switch(token)
            self.logger.debug("switch in {}".format(greenlet.getcurrent()))
            if all((self._handle_async(token, r) for r in results)):
                pass

            if self.exec_state == 'running':
                self.reader.switch(token)
                self.logger.debug("switch in {}".format(greenlet.getcurrent()))
                if not all((self._handle_async(token, r) for r in results)):
                    return

            if self.exec_state == 'stopped':
                self._display()
                r = results[-1]
                frame = r.results['frame']

                return frame['fullname'], frame['line']

        if cmd == 'interrupt':
            self.inferior_interrupt()

    def inferior_interrupt(self):
        self.process.send_signal(15)
        self.reader.parent = greenlet.getcurrent()
        self.reader.switch(token)

    def get_console_output(self):
        return self.console_output

    def get_locals(self):
        results = []

        if self.exec_state == 'stopped':
            token = self._send("-stack-list-variables --simple-values",
                               self._filter(results, 'ResultRecord', result_class='done'))
            self.reader.parent = greenlet.getcurrent()
            self.reader.switch(token)

            variables = results[0].results['variables']
            return variables
        else:
            return []

    def get_frames(self):
        results = []

        if self.exec_state == 'stopped':
            token = self._send("-stack-list-frames",
                               self._filter(results, 'ResultRecord', result_class='done'))
            self.reader.parent = greenlet.getcurrent()
            self.reader.switch(token)

            frames = results[0].results['stack']

            return frames
        else:
            return []

    def send_console_cmd(self, cmd):
        if cmd == 'n':
            self.exec('next', [])
            return
        if cmd == 'c':
            self.exec('continue', [])
            return
        if cmd == 'r':
            self.exec('run', [])
            return

        token = self._send("-interpreter-exec console " + cmd, self._handle)
        self.reader.parent = greenlet.getcurrent()
        self.reader.switch(token)

    def send_cmd(self, cmd):
        token = self._send(cmd, self._handle)
        self.reader.parent = greenlet.getcurrent()
        self.reader.switch(token)

    def quit(self):
        self._send("-gdb-exit", self._handle)

