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
  delcommand GDBMIDisplay
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
  command! GDBMIFrameUp call gdbmi#navigate('up')
  command! GDBMIFrameDown call gdbmi#navigate('down')
  command! GDBMIInterrupt call gdbmi#interrupt()
  command! GDBMIEvalWord call gdbmi#eval(expand('<cword>'))
  command! GDBMIDisplayWord call gdbmi#display(expand('<cword>'))

  command! -range GDBMIEvalRange call gdbmi#eval(gdbmi#util#get_selection(<f-args>))
  command! -range GDBMIDisplayRange call gdbmi#display(gdbmi#util#get_selection(<f-args>))

  command! -nargs=1 GDBMIDisplay call gdbmi#display(<f-args>)
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
      let l:tty = _gdbmi_start(t:gdbmi_buf_name)
      let t:gdbmi_channel_id = g:gdbmi#_channel_id
      return l:tty
    catch
      call gdbmi#util#print_error(
            \ 'gdbmi.nvim failed to load. '
            \ .'Try the :UpdateRemotePlugins command and restart Neovim.')
      return ''
    endtry
  endif
endfunction

function! s:StopGDBMI()
  if gdbmi#util#has_yarp()
    call t:gdbmi_yarp.request('_gdbmi_stop')
  else
    call gdbmi#util#rpcrequest('gdbmi_stop')
  endif
endfunction

function! gdbmi#init#Spawn(cmd) abort
  if has('nvim')
    if !has('python3')
      call gdbmi#util#print_error(
            \ 'gdbmi.nvim requires Neovim with Python3 support("+python3")')
      return
    endif

    if !has('nvim-0.3.0')
      call gdbmi#util#print_error(
            \ 'gdbmi.nvim requires Neovim +v0.3.0')
      return
    endif
  endif

  sp | wincmd T

  call gdbmi#util#init()

  call gdbmi#keymaps#init()

  call gdbmi#display#init()

  if !g:gdbmi_count
    call s:DefineCommands()

    augroup GDBMI
      autocmd!
      autocmd BufEnter * call gdbmi#util#on_BufEnter()
      autocmd BufLeave * call gdbmi#util#on_BufLeave()
      autocmd BufWinEnter GDBMI_* call gdbmi#util#on_BufWinEnter()
      autocmd BufHidden GDBMI_* call gdbmi#util#on_BufHidden()
    augroup END
  endif
  let g:gdbmi_count += 1
  let t:gdbmi_buf_name = 'GDBMI_'.g:gdbmi_count

  exe 'augroup '. t:gdbmi_buf_name . ' | autocmd! | augroup END'
  let l:autocmd = printf('autocmd %s %s %s call gdbmi#init#teardown(%d)',
        \ t:gdbmi_buf_name, exists('#TermClose') ? 'TermClose' : 'BufDelete',
        \ t:gdbmi_buf_name, g:gdbmi_count)
  exec l:autocmd

  let l:tty = s:StartGDBMI()
  if empty(l:tty) | return | endif

  let l:cmd = a:cmd .' -q -f -ex "new-ui mi '. l:tty .'"'

  if exists('g:gdbmi_split_direction') && g:gdbmi_split_direction ==# 'vertical'
    vsp | wincmd l | enew
  else
    sp | wincmd j | enew
  endif

  if has('nvim')
    let t:gdbmi_gdb_job_id = termopen(l:cmd)
  else
    let t:gdbmi_gdb_buf_name = term_start(l:cmd, {'curwin': 1})
    let t:gdbmi_gdb_buf_id = bufnr(t:gdbmi_gdb_buf_name)
    let t:gdbmi_gdb_job_id = t:gdbmi_gdb_buf_id
  endif

  exec 'file '. t:gdbmi_buf_name
  let t:gdbmi_gdb_win = win_getid()
  startinsert
endfunction

function! gdbmi#init#teardown(count)
  let l:gdbmi_buf_name = 'GDBMI_'.a:count

  call gdbmi#util#clear_sign()

  call gdbmi#util#rpcnotify('gdbmi_stop', l:gdbmi_buf_name)

  if !g:gdbmi_count
    call s:UndefCommands()
    autocmd! l:gdbmi_buf_name
  endif

  if exists('t:gdbmi_gdb_job_id')
    tabclose
    if exists('g:gdbmi_delete_after_quit') && g:gdbmi_delete_after_quit
      exe 'bdelete! '.l:gdbmi_buf_name
    endif
  endif
endfunction

