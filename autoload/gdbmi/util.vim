function! gdbmi#util#print_error(msg) abort
  echohl Error | echomsg '[gdbmi]: ' . a:msg | echohl None
endfunction

function! gdbmi#util#has_yarp() abort
  return !has('nvim')
endfunction

function! gdbmi#util#sign_init() abort
  let s:bp_symbol = get(g:, 'gdbmi#sign#bp_symbol', 'B>')
  let s:pc_symbol = get(g:, 'gdbmi#sign#pc_symbol', '->')

  exe 'highlight default link GDBMIBreakpointSign'.t:gdbmi_buf_name.' Type'
  exe 'highlight default link GDBMIUnselectedPCSign'.t:gdbmi_buf_name.' NonText'
  exe 'highlight default link GDBMIUnselectedPCLine'.t:gdbmi_buf_name.' DiffChange'
  exe 'highlight default link GDBMISelectedPCSign'.t:gdbmi_buf_name.' Debug'
  exe 'highlight default link GDBMISelectedPCLine'.t:gdbmi_buf_name.' Visual'

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
  exe 'highlight link GDBMISelectedPCLine'.t:gdbmi_buf_name.' Normal'
  exe 'highlight link GDBMISelectedPCSign'.t:gdbmi_buf_name.' Normal'
  exe 'highlight link GDBMIBreakpointSign'.t:gdbmi_buf_name.' Normal'
endfunction

function! gdbmi#util#sign_reset() abort
  exe 'highlight link GDBMISelectedPCLine'.t:gdbmi_buf_name.' Visual'
  exe 'highlight link GDBMISelectedPCSign'.t:gdbmi_buf_name.' Debug'
  exe 'highlight link GDBMIBreakpointSign'.t:gdbmi_buf_name.' Type'
endfunction

function! gdbmi#util#init() abort
  let g:gdbmi_count += 1
  let t:gdbmi_buf_name = 'GDBMI_'.g:gdbmi_count

  let t:gdbmi_win_jump_window = 1
  let t:gdbmi_win_current_buf = -1

  let t:gdbmi_cursor_line = -1
  let t:gdbmi_cursor_sign_id = 0
  
  let t:gdbmi_breakpoints_sign_ids = []
  call gdbmi#util#sign_init()
endfunction

let s:gdbmi_enable_keymap_autocmd = 1

function! gdbmi#util#on_BufEnter() abort
  if !exists('t:gdbmi_gdb_job_id') || !s:gdbmi_enable_keymap_autocmd
    return
  endif

  call gdbmi#keymaps#dispatch_set()
endfunction

function! gdbmi#util#on_BufLeave() abort
  if !exists('t:gdbmi_gdb_job_id') || !s:gdbmi_enable_keymap_autocmd
    return
  endif

  call gdbmi#keymaps#dispatch_unset()
endfunction

function! gdbmi#util#on_BufWinEnter() abort
  if !exists('t:gdbmi_channel_id') | return | endif
  if t:gdbmi_buf_name ==# expand('<afile>')
    let t:gdbmi_gdb_win = win_getid()
  endif
endfunction

function! gdbmi#util#on_BufHidden() abort
  if !exists('t:gdbmi_channel_id') | return | endif
  if t:gdbmi_buf_name ==# expand('<afile>')
    let t:gdbmi_gdb_win = 0
  endif
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
  let l:target_buf = bufnr(a:file, 1)
  call bufload(l:target_buf)
  call setbufvar(l:target_buf, '&buflisted', v:true)
  let l:target_win = bufwinid(l:target_buf)
  if l:target_win == -1
    let l:target_win = win_getid(t:gdbmi_win_jump_window)
  endif

  if nvim_win_get_buf(l:target_win) != l:target_buf
    call nvim_win_set_buf(l:target_win, l:target_buf)
  endif

  call nvim_win_set_cursor(l:target_win, [str2nr(a:line), 1])
endfunction

function! gdbmi#util#jump_frame(file, line) abort
  if !filereadable(a:file)
    call gdbmi#util#clear_cursor_sign()
    return
  endif
  call gdbmi#util#jump(a:file, a:line)
  call gdbmi#util#set_cursor_sign(a:file, a:line)
endfunction

function! gdbmi#util#set_cursor_sign(file, line) abort
  let l:old = t:gdbmi_cursor_sign_id

  let t:gdbmi_win_current_buf = bufnr(a:file, 1)
  let t:gdbmi_new_cursor_line = a:line

  let t:gdbmi_cursor_sign_id = t:gdbmi_win_current_buf * 10000 + float2nr(fmod(l:old, 10000)) + 1
  if t:gdbmi_new_cursor_line != -1 && t:gdbmi_win_current_buf != -1
    call sign_place(t:gdbmi_cursor_sign_id,
          \ t:gdbmi_buf_name,
          \ 'GdbmiCurrentLine'.t:gdbmi_buf_name,
          \ t:gdbmi_win_current_buf,
          \ {'lnum': t:gdbmi_new_cursor_line})
  endif
  if l:old != 0
    call sign_unplace(t:gdbmi_buf_name, {'id': l:old})
  endif
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

  if exists('t:gdbmi_gdb_win') && !empty(t:gdbmi_gdb_win)
    call win_gotoid(t:gdbmi_gdb_win)
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
    execute t:gdbmi_win_jump_window . 'wincmd w'
  endif

  if t:gdbmi_cursor_sign_id > 0
    call sign_jump(t:gdbmi_cursor_sign_id, t:gdbmi_buf_name, t:gdbmi_cursor_sign_id / 10000)
  endif
endfunction

function! gdbmi#util#scroll(action) abort
  if !exists('t:gdbmi_channel_id') | return | endif
  execute 'noautocmd silent! ' . t:gdbmi_win_jump_window . 'wincmd w'
  execute "normal! " . a:action
  noautocmd silent! wincmd p
endfunction

"}}}


