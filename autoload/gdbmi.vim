function! gdbmi#SendLine(cmd)
  call jobsend(t:gdbmi_gdb_job_id, a:cmd."\<CR>")
endfunction

function! gdbmi#Interrupt()
  if !exists('t:gdbmi_gdb_job_id') | return | endif
  call jobsend(t:gdbmi_gdb_job_id, "\<C-c>")
endfunction

function! gdbmi#Send(cmd)
  if !exists('t:gdbmi_gdb_job_id') | return | endif
  call gdbmi#SendLine(a:cmd)
endfunction

function! gdbmi#Eval(expr)
  call gdbmi#Send(printf('print %s', a:expr))
endfunction

function! gdbmi#ToggleBreak()
  if !exists('t:gdbmi_gdb_job_id') | return | endif

  let l:buf = bufnr('%')
  let l:filename = expand('#'.l:buf.':p')

  let l:cmd = gdbmi#util#rpcrequest('breaktoggle', l:filename, l:buf)

  call gdbmi#Send(l:cmd)
endfunction
