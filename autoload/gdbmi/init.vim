let g:gdbmi_count = 0

function! s:UndefCommands()
  delcommand GDBMIDebugStop
  delcommand GDBMIBreakpointToggle
  delcommand GDBMIRun
  delcommand GDBMIUntil
  delcommand GDBMIContinue
  delcommand GDBMINext
  delcommand GDBMIStep
  delcommand GDBMIFinish
  delcommand GDBMIFrameUp
  delcommand GDBMIFrameDown
  delcommand GDBMIInterrupt
  delcommand GDBMIEvalWord
endfunction

function! s:DefineCommands()
  command! GDBMIDebugStop call gdbmi#kill()
  command! GDBMIBreakpointToggle call gdbmi#toggle_break()
  command! GDBMIRun call gdbmi#send('run')
  command! GDBMIUntil call gdbmi#send('until ' . line('.'))
  command! GDBMIContinue call gdbmi#send('c')
  command! GDBMINext call gdbmi#send('n')
  command! GDBMIStep call gdbmi#send('s')
  command! GDBMIFinish call gdbmi#send('finish')
  command! GDBMIFrameUp call gdbmi#send('up')
  command! GDBMIFrameDown call gdbmi#send('down')
  command! GDBMIInterrupt call gdbmi#interrupt()
  command! GDBMIEvalWord call gdbmi#eval(expand('<cword>'))
  command! -range GDBMIEvalRange call gdbmi#eval(gdbmi#util#get_selection(<f-args>))
endfunction

function! gdbmi#init#Spawn(cmd) abort

  sp | wincmd T

  call gdbmi#util#init()

  call gdbmi#keymaps#init()

  if !g:gdbmi_count
    call s:DefineCommands()

    augroup GDBMI
      autocmd!
      autocmd BufEnter * call gdbmi#util#on_BufEnter()
      autocmd BufLeave * call gdbmi#util#on_BufLeave()
    augroup END
  endif
  let g:gdbmi_count += 1

  let t:gdbmi_buf_name = 'GDBMI_'.g:gdbmi_count
  exec 'augroup '.t:gdbmi_buf_name
    autocmd!
    exec 'autocmd TermClose '.t:gdbmi_buf_name.' call gdbmi#init#teardown('.g:gdbmi_count.')'
  augroup END

  let l:tty = _gdbmi_start()

  let l:cmd = a:cmd .' -q -f -ex "new-ui mi '. l:tty .'"'

  sp | wincmd j | enew | let t:gdbmi_gdb_job_id = termopen(l:cmd)

  exec "file ".t:gdbmi_buf_name
  startinsert

endfunction

function! gdbmi#init#teardown(count)

  call gdbmi#util#clear_sign()

  call s:UndefCommands()

  if exists('t:gdbmi_gdb_job_id')
    tabclose
    if exists('g:gdbmi_delete_after_quit') && g:gdbmi_delete_after_quit
      exe 'bdelete! GDBMI_'.a:count
    endif
  endif
endfunction

