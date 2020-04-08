import os

from gdbmi_interface.gdbmi import Session
from gdbmi_interface.ui import ui

class GDBMI_rplugin():
    def __init__(self, vim):
        self.vim = vim
        ui.setVim(vim)

        self.sessions = {}
        self.master = None
        self.slave_path = ""

    def start(self, args):
        name = args[0]
        master, slave = os.openpty()
        slave_path = os.ttyname(slave)
        self.sessions[name] = Session(name, master, slave_path, ui)

    def getSlave(self, args):
        return self.sessions[args[0]].slave_path

    def stop(self, args):
        name = args[0]
        self.sessions[name].stop()
        del self.sessions[name]

    def breakswitch(self, args):
        session_name, filename, line = args
        session = self.sessions[session_name]
        bp_id = session.breakpoints_status(filename, line)

        if bp_id:
            return f"delete { bp_id }"
        else:
            return f"break { filename }:{ line }"

    def display(self, args):
        session_name, expr = args
        self.sessions[session_name].add_display(expr)

