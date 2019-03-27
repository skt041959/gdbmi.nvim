function! gdbmi#util#print_error(msg) abort
    echohl Error | echomsg '[gdbmi]: ' . a:msg | echohl None
endfunction

function! gdbmi#util#jump(file, line)
  let l:window = winnr()
  let l:mode = mode()
  exe t:gdbmi_win_jump_window 'wincmd w'
  let t:gdbmi_win_current_buf = bufnr('')
  let l:target_buf = bufnr(a:file, 1)

  if bufnr('%') != l:target_buf
    exe 'noswapfile buffer ' l:target_buf
    let t:gdbmi_win_current_buf = l:target_buf
    call refresh()
  endif

  exe 'normal! '.a:line.'G'
  let t:gdbmi_new_cursor_line = a:line
  exe l:window 'window w'
  call gdbmi#setCursorSign()
  if l:mode ==? 't' || l:mode ==? 'i'
    startinsert
  endif
endfunction

function! gdbmi#util#setCursorSign()
  let l:old = t:gdbmi_cursor_sign_id
  let t:gdbmi_cursor_sign_id = 4999 + (l:old != -1 ? 4998 - l:old : 0)
  let l:current_buf = getcurrenbuf() " TODO
  if t:gdbmi_new_cursor_line != -1 && l:current_buf != -1
    exe 'sign place '.t:gdbmi_cursor_sign_id.' name=GdbmiCurrentLine line='.t:gdbmi_new_cursor_line.' buffer='.l:current_buf
  endif
  if l:old != -1
    exe 'sign unplace '.l:old
  endif
endfunction

function! gdbmi#util#get_selection() abort
    let [l:lnum1, l:col1] = getpos("'<")[1:2]
    let [l:lnum2, l:col2] = getpos("'>")[1:2]
    let l:lines = getline(l:lnum1, l:lnum2)
    let l:lines[-1] = l:lines[-1][: l:col2 - (&selection ==? 'inclusive' ? 1 : 2)]
    let l:lines[0] = l:lines[0][l:col1 - 1:]
    return join(l:lines, "\n")
endfunction

function! s:gdbrpc(event, ...) abort
    if !exists('g:gdbmi#_channel_id')
        " throw '[gdbmi]: channel id not defined!'
        GdbmiInitializePython
    endif
    call rpcnotify(g:gdbmi#_channel_id, a:event, a:000)
endfunction

function! gdbmi#util#define_commands() abort "{{{
    nnoremap <silent> <Plug>GDBBreakSwitch
                \ :call <SID>gdbrpc("breakswitch", expand("%:p"), line('.'))<CR>

    nnoremap <silent> <Plug>GDBBreakProperty
                \ :call <SID>gdbrpc("bkpt_property", expand("%:p"), line('.'))<CR>

    command!      -nargs=*    -complete=customlist,<SID>gdb_launch_complete
                \ GDBLaunch          call <SID>gdbrpc("launchgdb", <f-args>)

endfunction
"}}}


