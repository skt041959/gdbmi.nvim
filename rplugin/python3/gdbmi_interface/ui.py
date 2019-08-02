class UI:

    def __init__(self):
        pass

    def setVim(self, vim):
        self.vim = vim

    def jump(self, file, line):
        self.vim.async_call(lambda : self.vim.call('gdbmi#util#jump', file, line))

    def jump_frame(self, frame):
        if 'fullname' in frame:
            self.vim.async_call(lambda : self.vim.call('gdbmi#util#jump_frame', frame['fullname'], frame['line']))
        else:
            self.vim.async_call(lambda : self.vim.call('gdbmi#util#clear_cursor_sign'))

    def set_breakpoint(self, id, file, line):
        self.vim.async_call(lambda : self.vim.call('gdbmi#util#set_breakpoint_sign', id, file, line))

    def del_breakpoint(self, id):
        self.vim.async_call(lambda : self.vim.call('gdbmi#util#del_breakpoint_sign', id))

    def del_cursor(self, thread_group_id):
        pass

    def float_display(self, context):
        self.vim.async_call(lambda: self.vim.call('gdbmi#display#float_display'), context)

    def virtual_display(self, context):
        self.vim.call('gdbmi#display#virtual_display', context)

    def async_error(self, msg):
        self.vim.async_call('gdbmi#util#print_error', msg)

    def error(self, msg):
        self.vim.call('gdbmi#util#print_error', msg)

ui = UI()

