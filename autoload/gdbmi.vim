function! gdbmi#send_line(cmd)
  call jobsend(t:gdbmi_gdb_job_id, a:cmd."\<CR>")
endfunction

function! gdbmi#interrupt()
  if !exists('t:gdbmi_gdb_job_id') | return | endif
  call jobsend(t:gdbmi_gdb_job_id, "\<C-c>")
endfunction

function! gdbmi#send(cmd)
  if !exists('t:gdbmi_gdb_job_id') | return | endif
  call gdbmi#send_line(a:cmd)
endfunction

function! gdbmi#eval(expr)
  call gdbmi#send(printf('print %s', a:expr))
endfunction

function! gdbmi#toggle_break()
  if !exists('t:gdbmi_gdb_job_id') | return | endif

  let l:buf = bufnr('%')
  let l:filename = expand('#'.l:buf.':p')
  let l:line = line('.')

  let l:cmd = gdbmi#util#rpcrequest('gdbmi_breaktoggle', l:filename, l:line)

  call gdbmi#send(l:cmd)
endfunction

function! gdbmi#display(expr)
  call gdbmi#util#rpcnotify('gdbmi_display', a:expr)
endfunction