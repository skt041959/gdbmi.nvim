let s:default_config = {
      \ 'key_until':        '<leader>du',
      \ 'key_continue':     '<leader>dc',
      \ 'key_next':         '<leader>dn',
      \ 'key_step':         '<leader>ds',
      \ 'key_finish':       '<leader>df',
      \ 'key_breakpoint':   '<leader>db',
      \ 'key_frameup':      '<leader>dU',
      \ 'key_framedown':    '<leader>dD',
      \ 'key_eval':         '<leader>de',
      \ 'set_tkeymaps': function('gdbmi#keymaps#SetT'),
      \ 'set_keymaps': function('gdbmi#keymaps#Set'),
      \ 'unset_keymaps': function('gdbmi#keymaps#Unset'),
      \ }

let s:default_keymaps = [
      \ ['n', 'key_until',    ':GDBMIUntil'],
      \ ['n', 'key_continue', ':GDBMIContinue'],
      \ ['n', 'key_next',     ':GDBMINext'],
      \ ['n', 'key_step',     ':GDBMIStep'],
      \ ['n', 'key_finish',   ':GDBMIFinish'],
      \ ['n', 'key_breakpoint',':GDBMIBreakpointToggle'],
      \ ['n', 'key_frameup',  ':GDBMIFramup'],
      \ ['n', 'key_framedown',':GDBMIFramdown'],
      \ ['n', 'key_eval',     ':GDBMIEvalWord'],
      \ ['v', 'key_eval',     ':GDBMIEvalRange'],
      \ ]

function! gdbmi#keymaps#Set()
  for keymap in s:default_keymaps
    if has_key(t:gdbmi_keymaps_config, keymap[1])
      let key = t:gdbmi_keymaps_config[keymap[1]]
      if !empty(key)
        exe keymap[0].'noremap <buffer> <silent> '.key.' '.keymap[2]'<cr>'
      endif
    endif
  endfor
endfunction

function! gdbmi#keymaps#Unset()
  for keymap in s:default_keymaps
    if has_key(t:gdbmi_keymaps_config, keymap[1])
      let key = t:gdbmi_keymaps_config[keymap[1]]
      if !empty(key)
        exe keymap[0].'unmap <buffer> '.key
      endif
    endif
  endfor
endfunction

function! gdbmi#keymaps#Init()
  if exists('g:gdbmi_config')
    let l:config = copy(g:gdbmi_config)
  else
    let l:config = copy(s:default_config)
  endif

  if exists('g:gdbmi_config_override')
    call extend(l:config, g:gdbmi_config_override)
  endif

  for key in keys(l:config)
    let varname = 'g:gdbmi_'.key
    if exists(varname)
      let l:config[key] = eval(varname)
    endif
  endfor

  let t:gdbmi_keymaps_config = l:config
endfunction

function! gdbmi#keymaps#DispatchSet()
  if !exists("t:gdbmi_keymaps_config") | return | endif
  try
    call t:gdbmi_keymaps_config['set_keymaps']()
  catch /.*/
  endtry
endfunction

function! gdbmi#keymaps#DispatchUnset()
  if !exists("t:gdbmi_keymaps_config") | return | endif
  try
    call t:gdbmi_keymaps_config['unset_keymaps']()
  catch /.*/
  endtry
endfunction
