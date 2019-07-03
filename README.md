# gdbmi.nvim


## description
This is a plugin for Neovim to integrate with GDB. It's not stable yet, might have some bugs.

This plugin use the power of Neovim remote plugin and GDB's new-ui command.
The new-ui command requires GDB version be 7.12+.
This plugin will create a pseudo tty in Python client to connect to GDB's second interface.

Currently, it doesn't support Native Python executable in Windows system, which don't have `os.openpty`.
You can use MingW Python or use Cygwin environment.


## features
- [x] keymap
- [x] line hint
- [x] support vim8
- [ ] show locals in float window

## default keymap

| Mapping | Command | Description|
|---------|---------|------------|
|`<leader>dn`|:GDBMINext| `next`|
|`<leader>ds`|:GDBMIStep| `step`|
|`<leader>dc`|:GDBMIContinue| `continue`|
|`<leader>df`|:GDBMIFinish| `finish`|
|`<leader>db`|:GDBMIBreakpointToggle| `break`|
|`<leader>dU`|:GDBMIFramup| `up`|
|`<leader>dD`|:GDBMIFramdown| `down`|
|`<leader>de`|:GDBMIEvalWord| `print <cword>`|

## change keymap

``` viml
let g:gdbmi_config = {
      \ 'key_until':        '<leader>du',
      \ 'key_continue':     '<leader>dc',
      \ 'key_next':         '<leader>dn',
      \ 'key_step':         '<leader>ds',
      \ 'key_finish':       '<leader>df',
      \ 'key_breakpoint':   '<leader>db',
      \ 'key_frameup':      '<leader>dU',
      \ 'key_framedown':    '<leader>dD',
      \ 'key_eval':         '<leader>de',
      \ 'key_ui_display':   '<leader>dw',
      \ 'key_ui_bringupgdb':  '<F7>',
      \ }
```

## inspire

+ [nvim-gdb](https://github.com/sakhnik/nvim-gdb)
+ [lldb.nvim](https://github.com/critiqjo/lldb.nvim)

