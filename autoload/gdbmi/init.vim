let g:gdbmi_count = 0

function! s:UndefCommands()
  delcommand GdbDebugStop
  delcommand GdbBreakpointToggle
  delcommand GdbBreakpointClearAll
  delcommand GdbRun
  delcommand GdbUntil
  delcommand GdbContinue
  delcommand GdbNext
  delcommand GdbStep
  delcommand GdbFinish
  delcommand GdbFrameUp
  delcommand GdbFrameDown
  delcommand GdbInterrupt
  delcommand GdbEvalWord
  delcommand GdbEvalRange
endfunction

function! s:DefineCommands()
  command! GDBMIDebugStop call gdbmi#Kill()
  command! GDBMIBreakpointToggle call gdbmi#ToggleBreak()
  command! GDBMIRun call gdbmi#Send("run")
  command! GDBMIUntil call gdbmi#Send("until " . line('.'))
  command! GDBMIContinue call gdbmi#Send("c")
  command! GDBMINext call gdbmi#Send("n")
  command! GDBMIStep call gdbmi#Send("s")
  command! GDBMIFinish call gdbmi#Send("finish")
  command! GDBMIFrameUp call gdbmi#Send("up")
  command! GDBMIFrameDown call gdbmi#Send("down")
  command! GDBMIInterrupt call gdbmi#Interrupt()
  command! GDBMIEvalWord call gdbmi#Eval(expand('<cword>'))
  command! -range GDBMIEvalRange call gdbmi#Eval(gdbmi#util#get_selection(<f-args>))
endfunction

function! gdbmi#init#Spawn(cmd) abort

  sp | wincmd T

  call gdbmi#util#Init()

  call gdbmi#keymaps#Init()

  if !g:gdbmi_count
    call s:DefineCommands()

    augroup GDBMI
      autocmd!
      autocmd BufEnter * call gdbmi#util#OnBufEnter()
      autocmd BufLeave * call gdbmi#util#OnBufLeave()
    augroup END
  endif
  let g:gdbmi_count += 1

  let l:tty = _gdbmi_start()

  let l:cmd = a:cmd .' -ex "new-ui mi '. l:tty .'"'

  sp | wincmd j | enew | let t:gdbmi_gdb_job_id = termopen(l:cmd)

  startinsert

endfunction
