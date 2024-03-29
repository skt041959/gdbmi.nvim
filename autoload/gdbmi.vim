function! gdbmi#send_line(cmd)
  if has('nvim')
    call chansend(t:gdbmi_gdb_job_id, a:cmd."\n")
  else
    call term_sendkeys(t:gdbmi_gdb_job_id, a:cmd."\<CR>")
  endif
endfunction

function! gdbmi#interrupt()
  if !exists('t:gdbmi_gdb_job_id') | return | endif
  call jobsend(t:gdbmi_gdb_job_id, "\<C-c>")
endfunction

function! gdbmi#send(cmd)
  if !exists('t:gdbmi_gdb_job_id') | return | endif
  call gdbmi#send_line(a:cmd)
endfunction

function! gdbmi#navigate(cmd)
  if !exists('t:gdbmi_gdb_job_id') | return | endif
  call gdbmi#send_line(a:cmd)
endfunction

function! gdbmi#eval(expr)
  call gdbmi#send(printf('print %s', a:expr))
endfunction

function! gdbmi#toggle_break_line()
  if !exists('t:gdbmi_gdb_job_id') | return | endif

  let l:buf = bufnr('%')
  let l:filename = expand('#'.l:buf.':p')
  let l:line = line('.')

  let l:cmd = gdbmi#util#rpcrequest('gdbmi_breaktoggle', t:gdbmi_buf_name, l:filename, l:line)

  call gdbmi#send(l:cmd)
endfunction

function! gdbmi#get_breakpoint_list() abort
  if !exists('t:gdbmi_gdb_job_id') | return | endif

  let g:gdbmi_jump_locations = gdbmi#util#rpcrequest('gdbmi_getbreakpoints', t:gdbmi_buf_name)

  doautocmd <nomodeline> User GDBMILocationChange
endfunction

function! gdbmi#break_expr(expr)
  call gdbmi#send(printf('break %s', a:expr))
endfunction

function! gdbmi#display(expr)
  call gdbmi#util#rpcnotify('gdbmi_display', t:gdbmi_buf_name, a:expr)
endfunction
