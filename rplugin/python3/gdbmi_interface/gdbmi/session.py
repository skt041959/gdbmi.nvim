#!/usr/bin/python

import os
import pty
import sys
import fcntl
import select
import logging
import functools
import re
from collections import deque
from greenlet import greenlet

from subprocess import Popen, PIPE

from .parse import GDBOutputParse, ParseError
from .parse import ResultRecord, AsyncRecord, StreamRecord

class Handled(object): pass


class ErrorArgumentsException(Exception):
    pass


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
    def __init__(self, debuggee, output, gdb="gdb"):
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

        self.exec_state = None

        self.debuggee = debuggee
        self.output = open(output, 'w')

        p = Popen(
            bufsize = 0,
            args = [
                gdb,
                '--return-child-result',
                '--quiet', # inhibit dumping info at start-up
                '--nx', # inhibit window interface
                '--nw', # ignore .gdbinit
                '--interpreter=mi2', # use GDB/MI v2
                #'--write', # to-do: allow to modify executable/cores?
                self.debuggee,
            ],
            stdin = PIPE, stdout = PIPE,
            close_fds = True
        )
        fl = fcntl.fcntl(p.stdout, fcntl.F_GETFL)
        fcntl.fcntl(p.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.process = p

        self.token = 0

        self.sender = greenlet(self._send)
        self.reader = greenlet(self._read)

        self.waiting_cmd = deque()

        if self.reader.switch(0):
            self.sendable = True

        self.logger.debug("session: {} gdb: {}".format(debuggee, gdb))

        master_fd = self.inferior_tty_set()
        self.debuggee_file = open(master_fd, 'w')

    def break_insert(self, location, handler = None):
        handler = self._handle_result
        token = self._send("-break-insert " + location, handler)
        self.reader.switch(token)

    def exec_continue(self, handler = None):
        return self._send("-exec-continue", handler)

    def exec_run(self, handler = None):
        return self._send("-exec-run", handler)

    def exec_return(self, value = None, handler = None):
        if value is None:
            return self._send("-exec-return", handler)
        return self._send("-exec-return " + str(value), handler)

    def _send(self, cmd, handler = None):
        if self.sendable:
            self.token += 1
            token = "%04d" % self.token
            buf = token + cmd + "\n"
            self.process.stdin.write(buf.encode('utf8'))

            self.logger.debug(["SENT[" + token +"]:", cmd])
            self.commands[token] = {'cmd': cmd, 'handler': handler}
            return token
        else:
            return None

    def _read(self, blocking = 0):
        #  import ipdb
        #  ipdb.set_trace()
        p = self.process
        parser = GDBOutputParse()
        while 1:
            rd = select.select([p.stdout], [], [], blocking)[0]
            if p.stdout in rd:
                try:
                    token, result = parser.parse(p.stdout.readline().decode('utf8'))
                    if token and self.commands.get(token, False):
                        self.commands[token]['handler'](result)
                    else:
                        if result is parser.GDB_PROMPT:
                            greenlet.getcurrent().parent.switch(True)
                        else:
                            self._handle(token, result)
                    blocking = 0
                except ParseError as e:
                    self.vim.err_write("[gdbmi]: gdb output parse error\n")

    def _handle_exec(self, token, obj):
        if obj.what == "stopped":
            self.exec_state = obj.what

    def _handle_result(self, token, obj):
        self.output.write(obj.What)
        self.output.flush()
        #  greenlet.getcurrent().parent.switch(Handled)

    def _handle_async(self, token, obj):
        self.output.write(obj.What)
        self.output.flush()
        #  greenlet.getcurrent().parent.switch(Handled)
        return True

    def _handle_stream(self, token, obj):
        self.output.write(obj.What)
        self.output.flush()
        return True
        #  greenlet.getcurrent().parent.switch(Handled)

    def _handle_notify(self, token, obj):
        if obj.what == "thread-group-added":
            tg = self._add_thread_group(obj.args)
            self.logger.info(tg)
            return True

        if obj.what == "thread-group-started":
            tg = self.thread_groups[obj.args['id']]
            tg['pid'] = obj.args['pid']
            self.logger.info(tg)
            return True

        if obj.what == "thread-created":
            tg = self.thread_groups[obj.args['group-id']]
            tg['threads'].add(obj.args['id'])
            self.logger.info(tg)
            return True

        if obj.what == "library-loaded":
            tg = self.thread_groups[obj.args['thread-group']]
            tg['dl'][obj.args['id']] = obj.args
            self.logger.info(tg)
            return True

        if obj.what == "breakpoint-modified":
            self._update_breakpoint(obj.args['bkpt'])
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

    def _handle(self, token, obj):
        handler = {
            'ResultRecord'   : self._handle_result,
            'AsyncRecord'    : self._handle_async,
            'StreamRecord'   : self._handle_stream,
        }.get(obj.What, None)

        if not (handler and handler(token, obj)):
            self.logger.warn(["IGN:", token, obj])
        else:
            self.output.write(obj.What)
            greenlet.getcurrent().parent.switch(Handled)

    def wait_for(self, stop_token = None):
        for token, obj in self.read(1):
            if token == stop_token:
                return True
        return False

    def inferior_tty_set(self):
        pid = os.getpid()
        (master, slave) = os.openpty()
        slave_node = "/proc/%d/fd/%d" % (pid, slave)
        self._send("-inferior-tty-set " + slave_node), master
        return"/proc/{0}/fd/{1}".format(pid, master)

    def do_breakswitch(self, **kwargs):
        filename = kwargs.pop('filename', None)
        line = kwargs.pop('line', None)
        if filename and line:
            l = filename + ':' + str(line)
        else:
            l = kwargs.pop('function')

        self.logger.debug("breakswitch at {}".format(l))
        return self.break_insert(location=l)

