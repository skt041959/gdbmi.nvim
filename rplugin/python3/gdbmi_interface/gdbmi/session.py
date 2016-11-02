#!/usr/bin/python

import os
import pty
import sys
import fcntl
import selectors
import logging
import functools
from threading import Thread, Event
from collections import deque

from collections import deque
from subprocess import Popen, PIPE

from .parse import GDBOutputParse, ParseError
from .parse import ResultRecord, AsyncRecord, StreamRecord
try:
    from ..hues import huestr
except:
    from hues import huestr


class ErrorArgumentsException(Exception): pass


class GDBStopped(Exception): pass


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
    def __init__(self, vim, debuggee, gdb="gdb"):
        """
        >>> p = Session("test/hello")
        """
        self.vim = vim
        self.async_call = vim.async_call

        self.logger = logging.getLogger(__name__)
        fh = logging.FileHandler('/home/skt/tmp/gdbmi.nvim.log')
        fh.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s @ '
            '%(filename)s:%(funcName)s:%(lineno)s] %(process)s - %(message)s'))
        self.logger.addHandler(fh)
        self.logger.setLevel(logging.DEBUG)

        self.buf = ""
        self.is_attached = False

        self.thread_groups = {}
        self.breakpoints = {}

        self.commands = {}
        self._callbacks = {}
        self._hijacked = {}

        self.debuggee = debuggee

        self.process = self._launch_gdb(debuggee, gdb)
        self.exec_state = 'ready'

        self.parser = GDBOutputParse()
        self.console_output = []
        self.token = 0
        self.last_valid_token = None
        self.gdb_stdout_buf = []
        self.gdb_stdout_objs = deque()

        self.sel = selectors.DefaultSelector()
        self.sel.register(self.process.stdout, selectors.EVENT_READ, self._gdb_stdout_handler)
        while True:
            events = self.sel.select(3)
            for key, mask in events:
                key.data(key.fileobj, mask)
            if not events:
                break

        self.reader = Thread(target=self._read, name="reader", args=(self.sel,))
        self.reader.start()

        self.logger.debug("session: {} gdb: {}".format(debuggee, gdb))

        #  master_fd = self.inferior_tty_set()
        #  self.debuggee_file = open(master_fd, 'w')
        #  self.sel.register(self.debuggee_file, selectors.EVENT_READ, self._debugee_stdout_handler)

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

    def _send(self, cmd, handler=None, **kwargs):
        self.token += 1
        token = "%04d" % self.token
        buf = token + cmd + "\n"
        self.process.stdin.write(buf.encode('utf8'))

        self.logger.debug("SENT[{0}]: {1}".format(token, huestr(cmd).green.colorized))
        self.commands[token] = {'cmd': cmd, 'handler': handler}
        self.commands[token].update(kwargs)
        return token

    def _read(self, selector):
        while True:
            events = selector.select()
            for key, mask in events:
                try:
                    key.data(key.fileobj, mask)
                except GDBStopped:
                    self.logger.error("GDBStopped")
                    return

    def _gdb_stdout_handler(self, fileobj, mask):
        line = fileobj.readline().decode('utf8')
        if line == '':
            raise GDBStopped
        self.logger.debug('RAW: ' + huestr(line).green.colorized)
        try:
            self._handle(line)
        except:
            err = "There was an exception in  "
            err += __name__
            self.logger.exception(err)

    def _debugee_stdout_handler(self, fileobj, mask):
        pass

    def _handle(self, line):
        def _ignore(token, obj):
            self.logger.warn(["IGN:", token, obj])
            return False

        self.gdb_stdout_buf.append(line)
        try:
            token, obj = self.parser.parse(line)
        except ParseError as e:
            raise e
        else:
            if obj is self.parser.GDB_PROMPT:
                token = self.last_valid_token
                self.logger.debug("handle token: {}, {} objs".format(token, len(self.gdb_stdout_objs)))
                command = self.commands.get(token, {'handler': None, 'waiting': None})
                inferior_handler = command.get('handler', None)
                event = command.get('waiting', None)
                while self.gdb_stdout_objs:
                    obj = self.gdb_stdout_objs.popleft()
                    self.logger.debug("obj {}".format(obj.What))
                    handler = {'ResultRecord'   : self._handle_result,
                               'AsyncRecord'    : self._handle_async,
                               'StreamRecord'   : self._handle_stream,
                               }.get(obj.What, _ignore)
                    handler(token, obj)
                    if inferior_handler is not None:
                        inferior_handler(token, obj)
                if event is not None:
                    event.set()
            else:
                if token:
                    self.last_valid_token = token
                self.gdb_stdout_objs.append(obj)

    def _handle_result(self, token, obj):
        self.logger.debug(obj.What)
        handled = False
        if obj.result_class == "done" or obj.result_class == "running":
            command = self.commands.get(token, None)

            if 'bkpt' in obj.results:
                self._update_breakpoint(obj.results['bkpt'])
            if command:
                command['state'] = obj.What
                callback = command.get('result_callback', None)
                if callback:
                    callback(obj)

            handled = True
        return handled

    def _handle_async(self, token, obj, **kwargs):
        self.logger.debug(obj.What)
        if obj.async_class == "NOTIFY_CLASS":
            if obj.name == "thread-group-added":
                self._add_thread_group(obj.results)
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
                if token:
                    command = self.commands.get(token, {'exec_callback': None})
                    callback = command.get('exec_callback', None)
                    if callback:
                        self.logger.debug("async calling exec callback")
                        self.async_call(callback, obj.results['frame']['fullname'], obj.results['frame']['line'])
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

    def wait_for(self, token):
        self.logger.debug("waiting for {}".format(token))
        return self.commands[token]['waiting'].wait()

    def inferior_tty_set(self):
        pid = os.getpid()
        (master, slave) = os.openpty()
        slave_node = "/proc/{0}/fd/{1}".format(pid, slave)
        token = self._send("-inferior-tty-set " + slave_node, waiting=Event())
        self.wait_for(token)

        return "/proc/{0}/fd/{1}".format(pid, master)

    def do_breakswitch(self, **kwargs):
        def get_bkptnumber(obj):
            nonlocal bkpt_number
            bkpt_number = obj.results['bkpt']['number']

        filename = kwargs.pop('filename', None)
        line = kwargs.pop('line', None)
        if filename and line:
            l = filename + ':' + str(line)
        else:
            l = kwargs.pop('function')

        self.logger.debug("breakswitch at {}".format(l))

        bkpt_number = None
        token = self._send("-break-insert " + l, waiting=Event(), result_callback = get_bkptnumber)
        self.wait_for(token)

        return bkpt_number

    def _filter(self, container, what, **kwargs):

        def f(token, obj):
            #  self.logger.debug(repr(obj))
            if obj.What == what:
                for k,v in kwargs.items():
                    if getattr(obj, k, None) != v:
                        break
                else:
                    container.append(obj)

        return f

    def do_exec(self, cmd, *args, callback=None):
        if cmd in ('run', 'next', 'step', 'continue', 'finish',
                       'next-instruction', 'step-instruction'):
            token = self._send("-exec-" + cmd + " " + " ".join(args), exec_callback=callback)
            return token

        if cmd == 'interrupt':
            self.inferior_interrupt()

    def inferior_interrupt(self):
        self.process.send_signal(2)

        return  True

    def get_console_output(self):
        return self.console_output

    def get_breakpoints(self):
        return self.breakpoints

    def get_locals(self):
        results = []

        if self.exec_state == 'stopped':
            token = self._send("-stack-list-variables --simple-values",
                               self._filter(results, 'ResultRecord', result_class='done'),
                               waiting=Event())

            self.wait_for(token)
            variables = results[0].results['variables']
            return variables
        else:
            return []

    def get_frames(self):
        results = []

        if self.exec_state == 'stopped':
            token = self._send("-stack-list-frames",
                               self._filter(results, 'ResultRecord', result_class='done'),
                               waiting=Event())
            self.wait_for(token)
            frames = results[0].results['stack']
            return frames
        else:
            return []

    @exception(logging.getLogger(__name__))
    def get_threads(self):
        results = []

        if self.exec_state == 'stopped':
            token = self._send("-thread-info",
                               self._filter(results, 'ResultRecord', result_class='done'),
                               waiting=Event())
            self.wait_for(token)
            threads = results[0].results['threads']
            return threads
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
        #  self.wait_for(token)

    def send_cmd(self, cmd):
        token = self._send(cmd, self._handle)

    def quit(self):
        self._send("-gdb-exit", self._handle)
        self.reader.join()

