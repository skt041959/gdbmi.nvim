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

  if !has('python3')
    call gdbmi#util#print_error(
          \ 'gdbmi.nvim requires Neovim with Python3 support("+python3")')
    return
  endif

  if has('nvim') && !has('nvim-0.3.0')
    call gdbmi#util#print_error(
          \ 'gdbmi.nvim requires Neovim +v0.3.0')
    return
  endif

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

  if has('nvim')
    let t:gdbmi_buf_name = 'GDBMI_'.g:gdbmi_count
    exec 'augroup '.t:gdbmi_buf_name
      autocmd!
      exec 'autocmd TermClose '.t:gdbmi_buf_name.' call gdbmi#init#teardown('.g:gdbmi_count.')'
    augroup END
  endif

  " try
    if gdbmi#util#has_yarp()
      let t:gdbmi_yarp = yarp#py3('gdbmi_interface')
      let l:tty = t:gdbmi_yarp.request('_gdbmi_start')
      let t:gdbmi#_channel_id = 1
    else
      let l:tty = _gdbmi_start()
    endif
  " catch
  "   if gdbmi#util#has_yarp()
  "     if !has('nvim') && !exists('*neovim_rpc#serveraddr')
  "       call gdbmi#util#print_error(
  "             \ 'gdbmi.nvim requires vim-hug-neovim-rpc plugin in Vim')
  "     endif
  "
  "     if !exists('*yarp#py3')
  "       call gdbmi#util#print_error(
  "             \ 'gdbmi.nvim requires nvim-yarp plugin')
  "     endif
  "   else
  "     call gdbmi#util#print_error(
  "           \ 'gdbmi.nvim failed to load. '
  "           \ .'Try the :UpdateRemotePlugins command and restart Neovim.')
  "   endif
  "   return
  " endtry

  let l:cmd = a:cmd .' -q -f -ex "new-ui mi '. l:tty .'"'

  sp | wincmd j | enew | let t:gdbmi_gdb_job_id = termopen(l:cmd)

  exec "file ".t:gdbmi_buf_name
  startinsert

endfunction

function! gdbmi#init#teardown(count)

  call gdbmi#util#clear_sign()

  if !g:gdbmi_count
    call s:UndefCommands()
  endif

  if exists('t:gdbmi_gdb_job_id')
    tabclose
    if exists('g:gdbmi_delete_after_quit') && g:gdbmi_delete_after_quit
      exe 'bdelete! GDBMI_'.a:count
    endif
  endif
endfunction

