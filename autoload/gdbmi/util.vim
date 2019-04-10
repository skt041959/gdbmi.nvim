function! gdbmi#util#print_error(msg) abort
    echohl Error | echomsg '[gdbmi]: ' . a:msg | echohl None
endfunction

function! gdbmi#util#Init()
  let t:gdbmi_win_jump_window = 1
  let t:gdbmi_win_current_buf = -1

  let t:gdbmi_cursor_line = -1
  let t:gdbmi_cursor_sign_id = -1
endfunction

function! gdbmi#util#OnBufEnter()
  if !exists('t:gdbmi_gdb_job_id')
    return
  endif

  if &buftype ==# 'terminal'
    return
  endif

  call gdbmi#keymaps#Set()
endfunction

function! gdbmi#util#OnBufLeave()
  if !exists('t:gdbmi_gdb_job_id')
    return
  endif

  if &buftype ==# 'terminal'
    return
  endif

  call gdbmi#keymaps#Unset()
endfunction


function! gdbmi#util#jump(file, line)
  let l:window = winnr()
  let l:mode = mode()
  exe t:gdbmi_win_jump_window.'wincmd w'
  let t:gdbmi_win_current_buf = bufnr('')
  let l:target_buf = bufnr(a:file, 1)

  if bufnr('%') != l:target_buf
    exe 'noswapfile buffer ' l:target_buf
    let t:gdbmi_win_current_buf = l:target_buf
  endif

  exe 'normal! '.a:line.'G'
  let t:gdbmi_new_cursor_line = a:line
  exe l:window.'wincmd w'
  call gdbmi#util#set_cursor_sign()
  if l:mode ==? 't' || l:mode ==? 'i'
    startinsert
  endif
endfunction

function! gdbmi#util#set_cursor_sign()
  let l:old = t:gdbmi_cursor_sign_id
  let t:gdbmi_cursor_sign_id = 4999 + (l:old != -1 ? 4998 - l:old : 0)
  let l:current_buf = t:gdbmi_win_current_buf
  if t:gdbmi_new_cursor_line != -1 && l:current_buf != -1
    exe 'sign place '.t:gdbmi_cursor_sign_id.' name=GdbmiCurrentLine line='.t:gdbmi_new_cursor_line.' buffer='.l:current_buf
  endif
  if l:old != -1
    exe 'sign unplace '.l:old
  endif
endfunction

function! gdbmi#util#set_breakpoint_sign(id, file, line)
  exe 'sign place '.(5000+a:id).' name=GdbmiBreakpoint line='.a:line.' file='.a:file
endfunction

function! gdbmi#util#get_selection(...) range
    let [l:lnum1, l:col1] = getpos("'<")[1:2]
    let [l:lnum2, l:col2] = getpos("'>")[1:2]
    let l:lines = getline(l:lnum1, l:lnum2)
    let l:lines[-1] = l:lines[-1][: l:col2 - (&selection ==? 'inclusive' ? 1 : 2)]
    let l:lines[0] = l:lines[0][l:col1 - 1:]
    return join(l:lines, "\n")
endfunction

function! gdbmi#util#rpcnotify(event, ...) abort
  if !exists('g:gdbmi#_channel_id') | return | endif

  call rpcnotify(g:gdbmi#_channel_id, a:event, a:000)
endfunction

function! gdbmi#util#rpcrequest(event, ...) abort
  if !exists('g:gdbmi#_channel_id') | return | endif

  return rpcrequest(g:gdbmi#_channel_id, a:event, a:000)
endfunction

"}}}


