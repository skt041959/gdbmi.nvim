function! gdbmi#util#print_error(msg) abort
  echohl Error | echomsg '[gdbmi]: ' . a:msg | echohl None
endfunction

function! gdbmi#util#has_yarp() abort
  if !g:gdbmi_use_yarp
    return v:false
  else
    runtime autoload/yarp.vim
    return exists('*yarp#py3')
  endif
endfunction

function! gdbmi#util#sign_init() abort
  let s:bp_symbol = get(g:, 'gdbmi#sign#bp_symbol', 'B>')
  let s:pc_symbol = get(g:, 'gdbmi#sign#pc_symbol', '->')

  highlight default GDBMIDefaultSelectedPCLine gui=bold,italic,underline
  call gdbmi#util#sign_reset()

  exe 'sign define GdbmiBreakpoint'.t:gdbmi_buf_name.
        \ ' text=' . s:bp_symbol .
        \ ' texthl=GDBMIBreakpointSign'.t:gdbmi_buf_name.
        \ ' linehl=GDBMIBreakpointLine'.t:gdbmi_buf_name

  exe 'sign define GdbmiCurrentLine'.t:gdbmi_buf_name.
        \ ' text=' . s:pc_symbol .
        \ ' texthl=GDBMISelectedPCSign'.t:gdbmi_buf_name.
        \ ' linehl=GDBMISelectedPCLine'.t:gdbmi_buf_name

  exe 'sign define GdbmiCurrentLine2'.t:gdbmi_buf_name.
        \ ' text=' . s:pc_symbol .
        \ ' texthl=GDBMIUnselectedPCSign'.t:gdbmi_buf_name.
        \ ' linehl=GDBMIUnselectedPCLine'.t:gdbmi_buf_name
endfunction

function! gdbmi#util#sign_hide() abort
  exe 'highlight GDBMISelectedPCLine'.t:gdbmi_buf_name.' guifg=NONE guibg=NONE'
  exe 'highlight GDBMISelectedPCSign'.t:gdbmi_buf_name.' guifg=NONE guibg=NONE'
  exe 'highlight GDBMIBreakpointSign'.t:gdbmi_buf_name.' guifg=NONE guibg=NONE'
endfunction

function! gdbmi#util#sign_reset() abort
  exe 'highlight link GDBMISelectedPCLine'.t:gdbmi_buf_name.' GDBMIDefaultSelectedPCLine'
  exe 'highlight link GDBMISelectedPCSign'.t:gdbmi_buf_name.' Debug'
  exe 'highlight link GDBMIBreakpointSign'.t:gdbmi_buf_name.' Type'
  " exe 'highlight link GDBMIUnselectedPCSign'.t:gdbmi_buf_name.' NonText'
  " exe 'highlight link GDBMIUnselectedPCLine'.t:gdbmi_buf_name.' DiffChange'
endfunction

function! gdbmi#util#init() abort
  let g:gdbmi_count += 1
  let t:gdbmi_buf_name = 'GDBMI_'.g:gdbmi_count

  let t:gdbmi_win_jump_window = 1
  let t:gdbmi_win_current_buf = -1

  let t:gdbmi_cursor_line = -1
  let t:gdbmi_cursor_sign_id = -1

  let t:gdbmi_breakpoints_sign_ids = []
  call gdbmi#util#sign_init()
endfunction

let s:gdbmi_enable_keymap_autocmd = 1

function! gdbmi#util#on_BufEnter() abort
  if !exists('t:gdbmi_gdb_job_id') || !s:gdbmi_enable_keymap_autocmd
    return
  endif

  if &buftype == 'nofile'
    return
  endif

  if &buftype ==# 'terminal' && bufname() !=# t:gdbmi_buf_name
    return
  endif

  call t:gdbmi_keymaps_config['set_keymaps']()
endfunction

function! gdbmi#util#on_BufLeave() abort
  if !exists('t:gdbmi_gdb_job_id') || !s:gdbmi_enable_keymap_autocmd
    return
  endif

  if &buftype == 'nofile'
    return
  endif

  if &buftype ==# 'terminal' && bufname() !=# t:gdbmi_buf_name
    return
  endif

  call t:gdbmi_keymaps_config['unset_keymaps']()
endfunction

function! gdbmi#util#on_TabLeave() abort
  if !exists('t:gdbmi_channel_id') | return | endif
  call gdbmi#util#sign_hide()
endfunction

function! gdbmi#util#on_TabEnter() abort
  if !exists('t:gdbmi_channel_id') | return | endif
  call gdbmi#util#sign_reset()
endfunction

function! gdbmi#util#clear_sign() abort
  call gdbmi#util#clear_cursor_sign()
  call gdbmi#util#clear_breakpoint_sign()
endfunction

function! gdbmi#util#jump(file, line) abort
  if bufloaded(a:file)
    let l:target_buf = bufnr(a:file, 0)
    let l:target_win_id = bufwinid(l:target_buf)
    if l:target_win_id == -1
      let l:target_win_id = win_getid(t:gdbmi_win_jump_window)
    endif
    call nvim_win_set_buf(l:target_win_id, l:target_buf)
  else
    let curr_win = winnr()
    execute 'noautocmd' t:gdbmi_win_jump_window 'wincmd w'
    drop +`=a:line` `=a:file`
    let l:target_buf = bufnr()
    let l:target_win_id = bufwinid(l:target_buf)
    execute 'noautocmd' curr_win 'wincmd w'
  endif

  call nvim_win_set_cursor(l:target_win_id, [str2nr(a:line), 1])
  return l:target_buf
endfunction

function! gdbmi#util#jump_frame(file, line) abort
  if !exists('t:gdbmi_channel_id') | return | endif
  if !filereadable(a:file)
    call gdbmi#util#clear_cursor_sign()
    return
  endif
  let t:gdbmi_win_current_buf = gdbmi#util#jump(a:file, a:line)
  call gdbmi#util#set_cursor_sign(a:file, a:line)
endfunction

function! gdbmi#util#set_cursor_sign(file, line) abort
  if t:gdbmi_cursor_sign_id > 0
    call sign_unplace(t:gdbmi_buf_name, {'id': t:gdbmi_cursor_sign_id})
  endif

  let t:gdbmi_cursor_sign_id = t:gdbmi_win_current_buf * 10000 + float2nr(fmod(t:gdbmi_cursor_sign_id, 10000)) + 1
  call sign_place(t:gdbmi_cursor_sign_id,
        \ t:gdbmi_buf_name,
        \ 'GdbmiCurrentLine'.t:gdbmi_buf_name,
        \ t:gdbmi_win_current_buf,
        \ {'lnum': a:line})
endfunction

function! gdbmi#util#clear_cursor_sign() abort
  if t:gdbmi_cursor_sign_id > 0
    call sign_unplace(t:gdbmi_buf_name, {'id': t:gdbmi_cursor_sign_id})
    let t:gdbmi_cursor_sign_id = 0
  endif
endfunction

function! gdbmi#util#set_breakpoint_sign(id, file, line) abort
  let l:target_buf = bufnr(a:file, 1)
  let l:sid = 5000 + a:id
  call add(t:gdbmi_breakpoints_sign_ids, l:sid)
  call sign_place(l:sid, t:gdbmi_buf_name, 'GdbmiBreakpoint'.t:gdbmi_buf_name, a:file, {'lnum': a:line})
endfunction

function! gdbmi#util#del_breakpoint_sign(id) abort
  let l:sid = 5000 + a:id
  let l:idx = index(t:gdbmi_breakpoints_sign_ids, l:sid)
  if l:idx >= 0
    call remove(t:gdbmi_breakpoints_sign_ids, l:idx)
    call sign_unplace(t:gdbmi_buf_name, {'id': l:sid})
  endif
endfunction

function! gdbmi#util#clear_breakpoint_sign() abort
  for id in t:gdbmi_breakpoints_sign_ids
    call sign_unplace(t:gdbmi_buf_name, {'id': id})
  endfor
  let t:gdbmi_breakpoints_sign_ids = []
endfunction

function! gdbmi#util#get_selection(...) abort
  let [l:lnum1, l:col1] = getpos("'<")[1:2]
  let [l:lnum2, l:col2] = getpos("'>")[1:2]
  let l:lines = getline(l:lnum1, l:lnum2)
  let l:lines[-1] = l:lines[-1][: l:col2 - (&selection ==? 'inclusive' ? 1 : 2)]
  let l:lines[0] = l:lines[0][l:col1 - 1:]
  return join(l:lines, "\n")
endfunction

function! gdbmi#util#bringupgdb() abort
  if !exists('t:gdbmi_channel_id') | return | endif

  let gdb_win = bufwinid(t:gdbmi_buf_name)
  if gdb_win != -1
    call win_gotoid(gdb_win)
    startinsert
  elseif bufexists(t:gdbmi_buf_name)
    exe 'botright split '.t:gdbmi_buf_name
    startinsert
  endif
endfunction

function! gdbmi#util#rpcnotify(event, ...) abort
  if !exists('t:gdbmi_channel_id') | return | endif

  if gdbmi#util#has_yarp()
    call t:gdbmi_yarp.notify(a:event, a:000)
  else
    call rpcnotify(t:gdbmi_channel_id, a:event, a:000)
  endif
endfunction

function! gdbmi#util#rpcrequest(event, ...) abort
  if !exists('t:gdbmi_channel_id') | return | endif

  if gdbmi#util#has_yarp()
    return t:gdbmi_yarp.request(a:event, a:000)
  else
    return rpcrequest(t:gdbmi_channel_id, a:event, a:000)
  endif
endfunction

function! gdbmi#util#jump_to_pcsign() abort
  if !exists('t:gdbmi_channel_id') | return | endif
  if &l:buftype ==# 'terminal'
    execute t:gdbmi_win_jump_window 'wincmd w'
  endif

  if t:gdbmi_cursor_sign_id > 0
    call sign_jump(t:gdbmi_cursor_sign_id, t:gdbmi_buf_name, t:gdbmi_cursor_sign_id / 10000)
  endif
endfunction

function! gdbmi#util#scroll(action) abort
  if !exists('t:gdbmi_channel_id') | return | endif
  let curr_win = winnr()
  execute 'noautocmd silent!' t:gdbmi_win_jump_window 'wincmd w'
  execute 'normal!' a:action
  execute 'noautocmd silent!' curr_win 'wincmd w'
endfunction

"}}}


