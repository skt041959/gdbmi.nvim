let s:default_config = {
      \ 'key_until':         '<leader>du',
      \ 'key_advance':       '<leader>da',
      \ 'key_continue':      '<leader>dc',
      \ 'key_next':          '<leader>dn',
      \ 'key_step':          '<leader>ds',
      \ 'key_finish':        '<leader>df',
      \ 'key_reverse_continue': '<leader>dC',
      \ 'key_reverse_next':     '<leader>dN',
      \ 'key_reverse_step':     '<leader>dS',
      \ 'key_reverse_finish':   '<leader>dF',
      \ 'key_breakpoint':    '<leader>db',
      \ 'key_frameup':       '<leader>dU',
      \ 'key_framedown':     '<leader>dD',
      \ 'key_eval':          '<leader>de',
      \ 'key_ui_display':    '<leader>dw',
      \ 'key_ui_bringupgdb': '<leader>d<space>',
      \ 'key_ui_tocode':     '<leader>dp',
      \ 'key_ui_scrolldown': '<down>',
      \ 'key_ui_scrollup':   '<up>',
      \ 'key_ui_scrollpagedown': '<pagedown>',
      \ 'key_ui_scrollpageup':   '<pageup>',
      \ 'set_keymaps': function('gdbmi#keymaps#set'),
      \ 'unset_keymaps': function('gdbmi#keymaps#unset'),
      \ }

let s:default_keymaps = [
      \ ['n', 'key_until',         '<cmd>GDBMIUntil<CR>'],
      \ ['n', 'key_advance',       '<cmd>GDBMIAdvance<CR>'],
      \ ['n', 'key_continue',      '<cmd>GDBMIContinue<CR>'],
      \ ['n', 'key_next',          '<cmd>GDBMINext<CR>'],
      \ ['n', 'key_step',          '<cmd>GDBMIStep<CR>'],
      \ ['n', 'key_finish',        '<cmd>GDBMIFinish<CR>'],
      \ ['n', 'key_reverse_continue', '<cmd>call gdbmi#send("reverse-c")<CR>'],
      \ ['n', 'key_reverse_next',     '<cmd>call gdbmi#send("reverse-n")<CR>'],
      \ ['n', 'key_reverse_step',     '<cmd>call gdbmi#send("reverse-s")<CR>'],
      \ ['n', 'key_reverse_finish',   '<cmd>call gdbmi#send("reverse-f")<CR>'],
      \ ['n', 'key_breakpoint',    '<cmd>GDBMIBreakpointToggle<CR>'],
      \ ['n', 'key_frameup',       '<cmd>GDBMIFrameUp<CR>'],
      \ ['n', 'key_framedown',     '<cmd>GDBMIFrameDown<CR>'],
      \ ['n', 'key_eval',          '<cmd>GDBMIEvalWord<CR>'],
      \ ['n', 'key_ui_display',    '<cmd>GDBMIDisplayWord<CR>'],
      \ ['n', 'key_ui_tocode',     '<cmd>call gdbmi#util#jump_to_pcsign()<CR>'],
      \ ['n', 'key_ui_bringupgdb', '<cmd>call gdbmi#util#bringupgdb()<CR>'],
      \ ['v', 'key_breakpoint',    ':GDBMIBreakpointExpr<CR>'],
      \ ['v', 'key_eval',          ':GDBMIEvalRange<CR>'],
      \ ['v', 'key_ui_display',    ':GDBMIDisplayRange<CR>'],
      \ ['t', 'key_ui_tocode',     '<cmd>call gdbmi#util#jump_to_pcsign()<CR>'],
      \ ['t', 'key_ui_scrolldown',     '<cmd>call gdbmi#util#scroll("3\<c-e>")<CR>'],
      \ ['t', 'key_ui_scrollup',       '<cmd>call gdbmi#util#scroll("3\<c-y>")<CR>'],
      \ ['t', 'key_ui_scrollpagedown', '<cmd>call gdbmi#util#scroll("\<c-d>")<CR>'],
      \ ['t', 'key_ui_scrollpageup',   '<cmd>call gdbmi#util#scroll("\<c-u>")<CR>'],
      \ ]

function! gdbmi#keymaps#set()
  for keymap in s:default_keymaps
    let key = get(t:gdbmi_keymaps_config, keymap[1], '')
    if !empty(key)
      exe printf('%snoremap <buffer> <silent> %s %s', keymap[0], key, keymap[2])
    endif
  endfor

endfunction

function! gdbmi#keymaps#unset()
  for keymap in s:default_keymaps
    if has_key(t:gdbmi_keymaps_config, keymap[1])
      let key = t:gdbmi_keymaps_config[keymap[1]]
      if !empty(key)
        exe keymap[0].'unmap <buffer> '.key
      endif
    endif
  endfor
endfunction

function! gdbmi#keymaps#init()
  let l:config = copy(get(g:, 'gdbmi_config', s:default_config))
  call extend(l:config, get(g:, 'gdbmi_config_override', {}))

  let t:gdbmi_keymaps_config = l:config
endfunction

function! gdbmi#keymaps#dispatch_set()
  if !exists('t:gdbmi_keymaps_config') | return | endif
  call t:gdbmi_keymaps_config['set_keymaps']()
endfunction

function! gdbmi#keymaps#dispatch_unset()
  if !exists('t:gdbmi_keymaps_config') | return | endif
  try
    call t:gdbmi_keymaps_config['unset_keymaps']()
  catch /.*/
  endtry
endfunction
