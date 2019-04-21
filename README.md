# gdbmi.nvim


## description
This is a plugin for neovim to integrate with GDB. The project is under heavy development.

This plugin use the power of neovim remote plugin and gdb's new-ui.
The new-ui command requires gdb version be 7.12+.
This plugin will create a pseudo tty in Python client to connect to gdb's second interface.
Currently, it doesn't support Native Python executable in Windows system, which don't have `os.openpty`.
You can use MingW Python or use Cygwin environment.


## features
- [x] keymap
- [x] line hint
- [x] support vim8
- [ ] show locals in float window


## inspire

+ [nvim-gdb](https://github.com/sakhnik/nvim-gdb)
+ [lldb.nvim](https://github.com/critiqjo/lldb.nvim)

