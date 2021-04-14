import os
import fcntl
import asyncio

from subprocess import Popen, PIPE

from gdbmi_interface.gdbmi.parse import (
    GDBOutputParse,
    ParseError,
    ResultRecord,
    AsyncRecord,
    StreamRecord,
)
from gdbmi_interface.log import getLogger, log_exceptions


class Session(object):
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
        self.handlers = {
            "ResultRecord": self._handle_result,
            "AsyncRecord": self._handle_async,
            "StreamRecord": self._handle_stream,
        }

        self.gdbmi = os.fdopen(self.gdbmi_interface_fd, mode="wb+", buffering=0)
        loop = asyncio.get_event_loop()
        loop.add_reader(self.gdbmi_interface_fd, self.read_task)

        logger = getLogger(__name__)
        self.debug, self.info, self.warn, self.error = (
            logger.debug,
            logger.info,
            logger.warn,
            logger.error,
        )
        self.debug(f"Session launched {name} {gdbmi_interface_fd} {slave_path}")

    def _send(self, cmd, **kwargs):
        self.token += 1
        self.commands[self.token] = {"cmd": cmd}
        self.commands[self.token].update(kwargs)

        buf = f"{ self.token :04}{ cmd }\n"
        self.gdbmi.write(buf.encode("utf8"))
        self.debug(buf)

        return self.token

    #  @log_exceptions(logger)
    def read_task(self):
        line = self.gdbmi.readline()
        if not line:
            raise GDBStopped
        self._handle(line)

    def _handle(self, line):
        def _ignore(token, obj):
            self.warn(["IGN:", token, obj])
            return False

        self.debug("\n" + repr(line))
        try:
            token, obj = self.parser.parse(line.decode("utf8").rstrip("\r\n") + "\n")
        except ParseError as e:
            raise e
        else:
            token = int(token) if token is not None else token
            if obj is None or obj is self.parser.GDB_PROMPT:
                return
            self.debug("obj {}".format(obj.What))
            self.handlers.get(obj.What, _ignore)(token, obj)
            event = self.commands.get(token, {}).get("waiting", None)
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

        command["state"] = obj.What
        command["result"] = obj
        if "event" in command:
            command["event"].set()
            self.debug(f"event of {token} set")

    def _handle_async_notify(self, token, obj, kwargs):
        if obj.name == "thread-group-added":
            self._add_thread_group(obj.results)
            return True

        elif obj.name == "thread-group-started":
            tg = self.thread_groups[obj.results["id"]]
            tg["pid"] = obj.results["pid"]
            return True

        elif obj.name == "thread-groups-exited":
            self._del_thread_group(obj.results["id"])
            self.ui.del_cursor(obj.results["id"])
            return True

        elif obj.name == "thread-created":
            tg = self.thread_groups[obj.results["group-id"]]
            tg["threads"].add(obj.results["id"])
            return True

        elif obj.name == "thread-selected":
            self.ui.jump_frame(obj.results["frame"])

        elif obj.name == "library-loaded":
            tg = self.thread_groups[obj.results["thread-group"]]
            tg["library"][obj.results["id"]] = obj.results
            return True

        elif obj.name.startswith("breakpoint-"):
            self._update_breakpoint(obj)

    def _handle_async_exe(self, token, obj, kwargs):
        self.exec_state = obj.name

        if obj.name == "running":
            return True

        elif obj.name == "stopped":
            frame = obj.results.get("frame", None)
            if frame is None:
                return True
            callback = self.commands.get(token, {}).get("exec_callback", None)
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

        elif obj.async_class == "EXEC_CLASS":
            return self._handle_async_exe(token, obj, kwargs)

        return False

    def _handle_stream(self, token, obj):
        #  self.debug(repr(obj))
        return True

    def _add_thread_group(self, info, group_id=None):
        if group_id is None:
            group_id = info["id"]
        tg = {
            "id": group_id,
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
            if ("filter" in to_call) and (not to_call["filter"](kwds)):
                continue
            tmp_kwds = dict(kwds)
            tmp_kwds.update(to_call)
            to_call["proc"](tmp_kwds)

    def _update_breakpoint(self, obj):
        if obj.name == "breakpoint-deleted":
            info = self.breakpoints.pop(obj.results["id"], {})
            if "fullname" in info:
                self.ui.del_breakpoint(int(info["number"]))
            if "multi" in info:
                for i in info["multi"]:
                    self.ui.del_breakpoint(int(i["number"].replace(".", "")))
        else:
            info = obj.results["bkpt"]
            if isinstance(info, list):
                d = self.breakpoints.setdefault(info[0]["number"], {})
                d.update(info[0])
                d["multi"] = info[1:]
                if obj.name == "breakpoint-created":
                    for i in info[1:]:
                        if "fullname" in i:
                            self.debug("set_breakpoint %s:%s", i["fullname"], i["line"])
                            self.ui.set_breakpoint(
                                int(i["number"].replace(".", "")), i["fullname"], i["line"]
                            )
            else:
                self.breakpoints.setdefault(info["number"], {}).update(info)
                if obj.name == "breakpoint-created" and "fullname" in info:
                    self.ui.set_breakpoint(int(info["number"]), info["fullname"], info["line"])
                    self.ui.jump(info["fullname"], info["line"])

    def breakpoints_status(self, filename, line):
        for number, bkpt in self.breakpoints.items():
            if bkpt["type"] == "breakpoint" and bkpt["addr"] != "<MULTIPLE>":
                if int(bkpt["line"]) == int(line) and bkpt["fullname"] == filename:
                    return number
        else:
            return 0

    def get_breakpoints(self):
        results = []
        for number, bkpt in self.breakpoints.items():
            if bkpt["type"] == "breakpoint" and bkpt["addr"] != "<MULTIPLE>":
                results.append({"filename": bkpt["fullname"], "lnum": bkpt["line"], "text": ""})
        return results

    def wait_for(self, token):
        self.debug("waiting for {}".format(token))
        return self.commands[token]["waiting"].wait()

    def do_exec(self, cmd, *args, callback=None):
        if cmd in (
            "run",
            "next",
            "step",
            "continue",
            "finish",
            "next-instruction",
            "step-instruction",
        ):
            token = self._send("-exec-" + cmd + " " + " ".join(args), exec_callback=callback)
            return token

    def add_display(self, expr):
        self._display_exprs[expr] = {}
        self.debug(self._display_exprs)

    def _query_display(self, frame):
        self.debug(frame)
        result = self._query_display_expr(frame)
        #  self.debug(result)

        self._gather_result(result)

    def _query_display_expr(self, frame):
        result = {}
        for expr, values in self._display_exprs.items():
            ev = asyncio.Event()
            token = self._send(f"-data-evaluate-expression {expr}", event=ev)
            result[token] = (ev, frame, values)

        return result

    def _gather_result(self, result):
        async def one_expr(token, ev, frame, values):
            await ev.wait()
            obj = self.commands[token]["result"]
            values.setdefault(frame["addr"], []).append(
                obj.results if obj.result_class == "done" else None
            )
            self.debug(values)

        coros = [one_expr(token, *t_values) for token, t_values in result.items()]
        asyncio.gather(*coros)
        #  task = asyncio.ensure_future(asyncio.gather(*coros))
        #  task.add_done_callback(lambda : self.debug("all expr get value"))

    def stop(self):
        loop = asyncio.get_event_loop()
        loop.remove_reader(self.gdbmi_interface_fd)


class GDBStopped(Exception):
    pass
