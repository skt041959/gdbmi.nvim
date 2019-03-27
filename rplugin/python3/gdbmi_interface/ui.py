class VimWin:

    def __init__(self, vim, win, cursor, client, breakpoint, keymaps):
        self.vim = vim

    def jump(self, file, line):
        self.vim.call('gdbmi#jump')

