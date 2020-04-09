let s:default_config = {
      \ 'key_until':        '<leader>du',
      \ 'key_advance':      '<leader>da',
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
      \ 'set_keymaps': function('gdbmi#keymaps#set'),
      \ 'unset_keymaps': function('gdbmi#keymaps#unset'),
      \ }

let s:default_keymaps = [
      \ ['n', 'key_until',    ':GDBMIUntil'],
      \ ['n', 'key_advance',  ':GDBMIAdvance'],
      \ ['n', 'key_continue', ':GDBMIContinue'],
      \ ['n', 'key_next',     ':GDBMINext'],
      \ ['n', 'key_step',     ':GDBMIStep'],
      \ ['n', 'key_finish',   ':GDBMIFinish'],
      \ ['n', 'key_breakpoint',':GDBMIBreakpointToggle'],
      \ ['n', 'key_frameup',  ':GDBMIFrameUp'],
      \ ['n', 'key_framedown',':GDBMIFrameDown'],
      \ ['n', 'key_eval',     ':GDBMIEvalWord'],
      \ ['n', 'key_ui_display',':GDBMIDisplayWord'],
      \ ['v', 'key_eval',     ':GDBMIEvalRange'],
      \ ['v', 'key_ui_display',':GDBMIDisplayRange'],
      \ ]

let s:default_plug_keymaps = [
      \ ['n', 'key_ui_bringupgdb', '<plug>GDBMIBringupGDB'],
      \ ]

function! gdbmi#keymaps#set()
  for keymap in s:default_keymaps
    let key = get(t:gdbmi_keymaps_config, keymap[1], '')
    if !empty(key)
      exe keymap[0].'noremap <buffer> <silent> '.key.' '.keymap[2].'<cr>'
    endif
  endfor

  for keymap in s:default_plug_keymaps
    let key = get(t:gdbmi_keymaps_config, keymap[1], '')
    if !empty(key)
      exe keymap[0].'map <buffer> <silent> '.key.' '.keymap[2]
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

  noremap <plug>GDBMIBringupGDB :call gdbmi#util#bringupgdb()<CR>
  nnoremap <leader>dp :call gdbmi#util#jump_to_pcsign()<CR>
endfunction

function! gdbmi#keymaps#dispatch_set()
  if !exists('t:gdbmi_keymaps_config') | return | endif
  try
    call t:gdbmi_keymaps_config['set_keymaps']()
  catch /.*/
  endtry
endfunction

function! gdbmi#keymaps#dispatch_unset()
  if !exists('t:gdbmi_keymaps_config') | return | endif
  try
    call t:gdbmi_keymaps_config['unset_keymaps']()
  catch /.*/
  endtry
endfunction
