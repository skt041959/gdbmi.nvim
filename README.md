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

`:GDBMILaunch /usr/bin/gdb --pid <pid>`

## Keymap

  |Default Mapping   |Mode   |Command                  |Description|
  |----------------- |------ |------------------------ |------------------------------|
  |`<leader>dn`      |n      |:GDBMINext               |`next`|
  |`<leader>ds`      |n      |:GDBMIStep               |`step`|
  |`<leader>dc`      |n      |:GDBMIContinue           |`continue`|
  |`<leader>da`      |n      |:GDBMIAdvance            |`advance`|
  |`<leader>du`      |n      |:GDBMIUntil              |`until`|
  |`<leader>df`      |n      |:GDBMIFinish             |`finish`|
  |`<leader>db`      |n,v    |:GDBMIBreakpointToggle   |`break`|
  |`<leader>dU`      |n      |:GDBMIFrameUp            |`up`|
  |`<leader>dD`      |n      |:GDBMIFrameDown          |`down`|
  |`<leader>de`      |n,v    |:GDBMIEvalWord           |`print <cword>`|
  |`<leader>dp`      |n      |                         |jump to the current line in code window|
  |`<leader>dd`      |n      |                         |jump to or raise up the gdb window|
  |`<up>`            |t      |                         |scroll code window up|
  |`<down>`          |t      |                         |scroll code window down|
  |`<pageup>`        |t      |                         |scroll code window page up|
  |`<pagedown>`      |t      |                         |scroll code window page down|

### Change keymap

``` {.viml}
let g:gdbmi_config = {
      \ 'key_until':             '<leader>du',
      \ 'key_advance':           '<leader>da',
      \ 'key_continue':          '<leader>dc',
      \ 'key_next':              '<leader>dn',
      \ 'key_step':              '<leader>ds',
      \ 'key_finish':            '<leader>df',
      \ 'key_reverse_continue':  '<leader>dC',
      \ 'key_reverse_next':      '<leader>dN',
      \ 'key_reverse_step':      '<leader>dS',
      \ 'key_reverse_finish':    '<leader>dF',
      \ 'key_breakpoint':        '<leader>db',
      \ 'key_frameup':           '<leader>dU',
      \ 'key_framedown':         '<leader>dD',
      \ 'key_eval':              '<leader>de',
      \ 'key_ui_bringupgdb':     '<leader>dd',
      \ 'key_ui_tocode':         '<leader>dp',
      \ 'key_ui_scrolldown':     '<down>',
      \ 'key_ui_scrollup':       '<up>',
      \ 'key_ui_scrollpagedown': '<pagedown>',
      \ 'key_ui_scrollpageup':   '<pageup>',
      \ }
```
or
``` {.viml}
let g:gdbmi_config_override = {
      \ 'key_continue':          '<F5>',
      \ }
```

## To-do
- fix bringing up gdb in different tabpage
- add support for multi inferior

## Inspire

+ [nvim-gdb](https://github.com/sakhnik/nvim-gdb)
+ [lldb.nvim](https://github.com/critiqjo/lldb.nvim)

