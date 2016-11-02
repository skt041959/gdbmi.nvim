function! gdbmi#util#print_error(msg) abort
    echohl Error | echomsg '[gdbmi]: ' . a:msg | echohl None
endfunction

function! gdbmi#util#goto_last_frame(filename, line) abort
    let l:bufnr = bufnr(a:filename)
    try
        buffer +a:line l:bufnr
    catch
        call gdbmi#util#print_error(l:bufnr)
    endtry
endfunction

function! s:gdbcomplete(arg, line, pos) abort
    return []
endfunction

function! s:gdb_exec_complete(arg, ...) abort
    return ['run', 'next', 'step', 'continue', 'finish',
                \'next-instruction', 'step-instruction', 'interrupt']
endfunction

function! s:gdbnotify(event, ...) abort
    if !exists('g:gdbmi#_channel_id')
        throw 'GDB: channel id not defined!'
    endif
    " call gdbmi#util#print_error(string(a:000))
    call rpcnotify(g:gdbmi#_channel_id, a:event, a:000)
endfun


function! gdbmi#util#define_commands() abort "{{{
    command!      -nargs=*    -complete=customlist,<SID>gdbcomplete
                \ GDBLaunch          call <SID>gdbnotify("launchgdb", <f-args>)

    nnoremap <silent> <Plug>GDBBreakSwitch
               \ :call <SID>gdbnotify("breakswitch", expand("%:p"), line('.'))<CR>
    "vnoremap <silent> <Plug>LLStdInSelected
    "        \ :<C-U>call <SID>llnotify("stdin", lldb#util#get_selection())<CR>

    command!      -nargs=+    -complete=customlist,<SID>gdb_exec_complete
                \ GDBExec          call <SID>gdbnotify("exec", <f-args>)

    command!     GDBQuit     call <SID>gdbnotify("quitgdb")
endfunction
"}}}


