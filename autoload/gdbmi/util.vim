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

function! s:gdb_exec_complete(arglead, ...) abort
    let l:exec_subcommand = ['run', 'next', 'step', 'continue', 'finish',
                \'next-instruction', 'step-instruction', 'interrupt']
    return sort(filter(l:exec_subcommand, 'stridx(v:val, a:arglead) == 0'))
endfunction

function! s:gdbnotify(event, ...) abort
    if !exists('g:gdbmi#_channel_id')
        throw '[gdbmi]: channel id not defined!'
    endif
    " call gdbmi#util#print_error(string(a:000))
    call rpcnotify(g:gdbmi#_channel_id, a:event, a:000)
endfun


function! gdbmi#util#define_commands() abort "{{{
    nnoremap <silent> <Plug>GDBBreakSwitch
                \ :call <SID>gdbnotify("breakswitch", expand("%:p"), line('.'))<CR>

    nnoremap <silent> <Plug>GDBBreakProperty
                \ :call <SID>gdbnotify("bkpt_property", expand("%:p"), line('.'))<CR>

    command!      -nargs=*    -complete=customlist,<SID>gdbcomplete
                \ GDBLaunch          call <SID>gdbnotify("launchgdb", <f-args>)

    command!      -nargs=+    -complete=customlist,<SID>gdb_exec_complete
                \ GDBExec          call <SID>gdbnotify("exec", <f-args>)

    command!     GDBQuit     call <SID>gdbnotify("quitgdb")

    nnoremap <silent> <Plug>GDBRuntoCursor
                \ :call <SID>gdbnotify("exec", "runtocursor", expand("%:p"), line('.'))<CR>
    "vnoremap <silent> <Plug>LLStdInSelected
    "        \ :<C-U>call <SID>llnotify("stdin", lldb#util#get_selection())<CR>
    nnoremap <silent> <Plug>GDBBreakModify
                \ :call <SID>gdbnotify("bkpt_modify")<CR>

endfunction
"}}}


