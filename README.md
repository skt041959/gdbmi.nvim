# gdbmi.nvim


## Description
This is a plugin for Neovim to integrate with GDB. It's not stable yet, might have some bugs.

This plugin use the power of Neovim remote plugin and GDB's new-ui command.
The new-ui command requires GDB version be 7.12+.
This plugin will create a pseudo tty in Python client to connect to GDB's second interface.

Currently, it doesn't support Native Python executable in Windows system, which don't have `os.openpty`.
You can use MingW Python or use Cygwin environment.


## Features
- [x] keymap
- [x] line hint
- [x] support vim8
- [ ] show locals in float window

## Get started

`:GDBMILaunch /usr/bin/gdb a.out`

or launch with any argument

`:GDBMILaunch /usr/bin/gdb --pid 'pid'`

## Keymap

| Default Mapping | Command | Description|
|-----------------|---------|------------|
|`<leader>dn`|:GDBMINext| `next`|
|`<leader>ds`|:GDBMIStep| `step`|
|`<leader>dc`|:GDBMIContinue| `continue`|
|`<leader>da`|:GDBMIAdvance| `advance`|
|`<leader>du`|:GDBMIUntil| `until`|
|`<leader>df`|:GDBMIFinish| `finish`|
|`<leader>db`|:GDBMIBreakpointToggle| `break`|
|`<leader>dU`|:GDBMIFrameUp| `up`|
|`<leader>dD`|:GDBMIFrameDown| `down`|
|`<leader>de`|:GDBMIEvalWord| `print <cword>`|

### Change keymap

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

## To-do
- fix bringing up gdb in different tabpage
- fix BufReadPost event in new buffer
- add support for multi inferior

## Inspire

+ [nvim-gdb](https://github.com/sakhnik/nvim-gdb)
+ [lldb.nvim](https://github.com/critiqjo/lldb.nvim)

