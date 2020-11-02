let g:gdbmi_count = 0

function! s:UndefCommands()
  delcommand GDBMIDebugStop
  delcommand GDBMIBreakpointToggle
  delcommand GDBMIRun
  delcommand GDBMIUntil
  delcommand GDBMIAdvance
  delcommand GDBMIContinue
  delcommand GDBMINext
  delcommand GDBMIStep
  delcommand GDBMIFinish
  delcommand GDBMIFrameUp
  delcommand GDBMIFrameDown
  delcommand GDBMIInterrupt
  delcommand GDBMIEvalWord
  delcommand GDBMIDisplay
endfunction

function! s:DefineCommands()
  command! GDBMIDebugStop call gdbmi#kill()
  command! GDBMIBreakpointToggle call gdbmi#toggle_break_line()
  command! GDBMIRun call gdbmi#send('run')
  command! GDBMIUntil call gdbmi#send('until ' . line('.'))
  command! GDBMIAdvance call gdbmi#send('advance '.expand('<cword>'))
  command! GDBMIContinue call gdbmi#send('c')
  command! GDBMINext call gdbmi#send('n')
  command! GDBMIStep call gdbmi#send('s')
  command! GDBMIFinish call gdbmi#send('finish')
  command! GDBMIFrameUp call gdbmi#navigate('up')
  command! GDBMIFrameDown call gdbmi#navigate('down')
  command! GDBMIInterrupt call gdbmi#interrupt()
  command! GDBMIEvalWord call gdbmi#eval(expand('<cword>'))
  command! GDBMIDisplayWord call gdbmi#display(expand('<cword>'))

  command! -range GDBMIEvalRange call gdbmi#eval(gdbmi#util#get_selection(<f-args>))
  command! -range GDBMIDisplayRange call gdbmi#display(gdbmi#util#get_selection(<f-args>))
  command! -range GDBMIBreakpointExpr call gdbmi#break_expr(gdbmi#util#get_selection(<f-args>))

  command! -nargs=1 GDBMIDisplay call gdbmi#display(<f-args>)
endfunction

function! s:InitAutocmd()
  augroup GDBMI
    autocmd!
    autocmd BufEnter * call gdbmi#util#on_BufEnter()
    autocmd BufLeave * call gdbmi#util#on_BufLeave()
    autocmd BufWinEnter GDBMI_* call gdbmi#util#on_BufWinEnter()
    autocmd BufHidden GDBMI_* call gdbmi#util#on_BufHidden()
    autocmd TabLeave * call gdbmi#util#on_TabLeave()
    autocmd TabEnter * call gdbmi#util#on_TabEnter()
    autocmd TermClose GDBMI_* call gdbmi#init#teardown()
  augroup END
endfunction

function! s:StartGDBMI()
  if gdbmi#util#has_yarp()
    try
      let t:gdbmi_yarp = yarp#py3('gdbmi_interface')
      let l:tty = t:gdbmi_yarp.request('_gdbmi_start', t:gdbmi_buf_name)
      let g:gdbmi#_channel_id = 1
      let t:gdbmi_channel_id = g:gdbmi#_channel_id
      return l:tty
    catch
      echo v:exception
      if !has('nvim') && !exists('*neovim_rpc#serveraddr')
        call gdbmi#util#print_error(
              \ 'gdbmi.nvim requires vim-hug-neovim-rpc plugin in Vim')
      endif

      if !exists('*yarp#py3')
        call gdbmi#util#print_error(
              \ 'gdbmi.nvim requires nvim-yarp plugin')
      endif
      return ''
    endtry
  else
    try
      call _gdbmi_start(t:gdbmi_buf_name)
      let t:gdbmi_channel_id = g:gdbmi#_channel_id
      return gdbmi#util#rpcrequest('gdbmi_getslave', t:gdbmi_buf_name)
    catch
      echo v:exception
      call gdbmi#util#print_error(
            \ 'gdbmi.nvim failed to load. '
            \ .'Try the :UpdateRemotePlugins command and restart Neovim.')
      return ''
    endtry
  endif
endfunction

function! s:CheckPrerequisite() abort
  if has('nvim')
    if !has('python3')
      call gdbmi#util#print_error(
            \ 'gdbmi.nvim requires Neovim with Python3 support("+python3")')
      return v:false
    endif

    if !has('nvim-0.3.0')
      call gdbmi#util#print_error(
            \ 'gdbmi.nvim requires Neovim +v0.3.0')
      return v:false
    endif
  endif

  return v:true
endfunction

function! gdbmi#init#Spawn(cmd, mods, new_inferior_tty) abort
  if !s:CheckPrerequisite()
    return
  endif

  tab split
  if g:gdbmi_disable_autoread
    setglobal noautoread
  endif

  if !g:gdbmi_count
    call s:DefineCommands()
    call s:InitAutocmd()
  endif
  call gdbmi#util#init()

  call gdbmi#keymaps#init()

  call gdbmi#display#init()

  let l:new_ui_tty = s:StartGDBMI()
  if empty(l:new_ui_tty)
    call gdbmi#util#print_error(
          \ 'gdbmi.nvim remote plugin failed initialize')
    return
  endif

  let l:cmd = printf('%s split +let\ t:gdbmi_gdb_job_id=&l:channel term://%s', a:mods, a:cmd)
  exe l:cmd
  doautocmd BufEnter

  if bufexists(t:gdbmi_buf_name)
    bwipeout! `=t:gdbmi_buf_name`
  endif
  call nvim_buf_set_name(0, t:gdbmi_buf_name)

  let t:gdbmi_gdb_win = win_getid()
  call gdbmi#send('new-ui mi '.l:new_ui_tty)
  call gdbmi#send('set annotate 1')

  if a:new_inferior_tty !=? 'no'
    split term://tail -f /dev/null
    let t:gdbmi_inferior_tty = nvim_get_chan_info(&channel).pty
    if a:new_inferior_tty ==? 'hide'
      close
    endif
    call gdbmi#send('set inferior-tty '.t:gdbmi_inferior_tty)
  endif

  for cmd in g:gdbmi_run_commands
    call gdbmi#send(cmd)
  endfor
endfunction

function! gdbmi#init#teardown()
  redraw | echomsg "GDBMI Session closed ".expand('<amatch>')

  call gdbmi#util#clear_sign()

  call gdbmi#util#rpcnotify('gdbmi_stop', t:gdbmi_buf_name)

  if !g:gdbmi_count
    call s:UndefCommands()
    autocmd! `=t:gdbmi_buf_name`
  endif

  tabclose
  if !empty(g:gdbmi_delete_after_quit)
    bdelete! `=t:gdbmi_buf_name`
  endif
endfunction

