
# encoding: utf-8

class VimSign():
    """
    Classes responsible for placing signs in the Vim user interface.
    """
    SIGN_BREAKPOINT = "gdbsign_bpres"
    SIGN_PC_SELECTED = "gdbsign_pcsel"
    SIGN_PC_UNSELECTED = "gdbsign_pcunsel"

    # hopefully unique sign id (for `:sign place`)
    sign_id = 257

    def __init__(self, vim, name, filename, line, hidden):
        self.vim = vim
        self.id = VimSign.sign_id
        VimSign.sign_id += 1
        self.name = name
        self.filename = filename
        self.line = line
        if hidden:
            self.hidden = True
        else:
            self.show()

    def show(self):
        cmd = "sign place {id} name={name} line={line} file={filename}".format_map(self)
        self.vim.command(cmd)
        self.hidden = False

    def hide(self):
        cmd = "sign unplace {id}".format(id=self.id)
        self.vim.command(cmd)
        self.hidden = True

    def __getitem__(self, name):
        return getattr(self, name)

class BPSign(VimSign):
    def __init__(self, vim, filename, line, hidden=False):
        name = VimSign.SIGN_BREAKPOINT
        super(BPSign, self).__init__(vim, name, filename, line, hidden)

class PCSign(VimSign):
    def __init__(self, vim, filename, line, selected, hidden=False):
        self.selected = selected
        name = VimSign.SIGN_PC_SELECTED if selected else VimSign.SIGN_PC_UNSELECTED
        super(PCSign, self).__init__(vim, name, filename, line, hidden)
