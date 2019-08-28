function! gdbmi#util#print_error(msg) abort
  echohl Error | echomsg '[gdbmi]: ' . a:msg | echohl None
endfunction

function! gdbmi#util#has_yarp() abort
  return !has('nvim')
endfunction

function! gdbmi#util#init() abort
  let t:gdbmi_win_jump_window = 1
  let t:gdbmi_win_current_buf = -1

  let t:gdbmi_cursor_line = -1
  let t:gdbmi_cursor_sign_id = -1
  
  let t:gdbmi_breakpoints_sign_ids = []
endfunction

let s:gdbmi_enable_keymap_autocmd = 1

function! gdbmi#util#on_BufEnter() abort
  if !exists('t:gdbmi_gdb_job_id')
    return
  endif

  if !s:gdbmi_enable_keymap_autocmd
    return
  endif

  if &buftype ==# 'terminal'
    return
  endif

  call gdbmi#keymaps#dispatch_set()
endfunction

function! gdbmi#util#on_BufLeave() abort
  if !exists('t:gdbmi_gdb_job_id')
    return
  endif

  if !s:gdbmi_enable_keymap_autocmd
    return
  endif

  if &buftype ==# 'terminal'
    return
  endif

  call gdbmi#keymaps#dispatch_unset()
endfunction

function! gdbmi#util#on_BufWinEnter() abort
  if t:gdbmi_buf_name ==# expand('<afile>')
    let t:gdbmi_gdb_win = win_getid()
  endif
endfunction

function! gdbmi#util#on_BufHidden() abort
  if t:gdbmi_buf_name ==# expand('<afile>')
    let t:gdbmi_gdb_win = 0
  endif
endfunction

function! gdbmi#util#clear_sign() abort
  call gdbmi#util#clear_cursor_sign()
  call gdbmi#util#clear_breakpoint_sign()
endfunction

function! gdbmi#util#jump(file, line) abort
  let l:target_buf = bufnr(a:file, 1)

  let s:gdbmi_enable_keymap_autocmd = 0

  if winbufnr(t:gdbmi_win_jump_window) != l:target_buf
    let l:eventignore = &eventignore
    set eventignore+=BufReadPost,BufEnter
    exe t:gdbmi_win_jump_window.'wincmd w'
    exe 'buffer '. l:target_buf
    exe 'normal! '. a:line.'G'
    redraw
    let &eventignore = l:eventignore
    doautoall BufReadPost
    doautoall BufEnter
    set buflisted
    exe winnr('#').'wincmd w'
  else
    exe 'noautocmd '.t:gdbmi_win_jump_window.'wincmd w'
    if a:line <= line('w0') || a:line >= line('w$')
      exe 'normal! '.a:line.'G'
    endif
    exe 'noautocmd '.winnr('#').'wincmd w'
  endif

  let s:gdbmi_enable_keymap_autocmd = 1
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

  let t:gdbmi_cursor_sign_id = 4999 + (l:old != -1 ? 4998 - l:old : 0)
  if t:gdbmi_new_cursor_line != -1 && t:gdbmi_win_current_buf != -1
    let l:cmd = printf('sign place %d name=GdbmiCurrentLine line=%d buffer=%d',
          \ t:gdbmi_cursor_sign_id, t:gdbmi_new_cursor_line, t:gdbmi_win_current_buf)
    exec l:cmd
  endif
  if l:old != -1
    exe 'sign unplace '.l:old
  endif
endfunction

function! gdbmi#util#clear_cursor_sign() abort
  if t:gdbmi_cursor_sign_id > 0
    exe 'sign unplace '.t:gdbmi_cursor_sign_id
  endif
endfunction

function! gdbmi#util#set_breakpoint_sign(id, file, line) abort
  let l:target_buf = bufnr(a:file, 1)
  let l:sid = 5000 + a:id
  call add(t:gdbmi_breakpoints_sign_ids, l:sid)
  let l:cmd = printf('sign place %d name=GdbmiBreakpoint line=%s file=%s', l:sid, a:line, a:file)
  exec l:cmd
endfunction

function! gdbmi#util#del_breakpoint_sign(id) abort
  let l:sid = 5000 + a:id
  let l:idx = index(t:gdbmi_breakpoints_sign_ids, l:sid)
  if l:idx >= 0
    call remove(t:gdbmi_breakpoints_sign_ids, l:idx)
    exec 'sign unplace '.l:sid
  endif
endfunction

function! gdbmi#util#clear_breakpoint_sign() abort
  for id in t:gdbmi_breakpoints_sign_ids
    exe 'sign unplace '.id
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
  if !empty(t:gdbmi_gdb_win)
    call win_gotoid(t:gdbmi_gdb_win)
  else
    exe 'botright split '.t:gdbmi_buf_name.'| wincmd b'
  endif
  startinsert
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

"}}}


