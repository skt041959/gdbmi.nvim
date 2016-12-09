function! gdbmi#util#print_error(msg) abort
    echohl Error | echomsg '[gdbmi]: ' . a:msg | echohl None
endfunction

function! gdbmi#util#get_selection() abort
    let [l:lnum1, l:col1] = getpos("'<")[1:2]
    let [l:lnum2, l:col2] = getpos("'>")[1:2]
    let l:lines = getline(l:lnum1, l:lnum2)
    let l:lines[-1] = l:lines[-1][: l:col2 - (&selection ==? 'inclusive' ? 1 : 2)]
    let l:lines[0] = l:lines[0][l:col1 - 1:]
    return join(l:lines, "\n")
endfunction

function! s:gdb_launch_complete(arglead, line, pos) abort
    return []
endfunction

function! s:gdb_exec_complete(arglead, ...) abort
    let l:exec_subcommand = ['run', 'next', 'step', 'continue', 'finish',
                \'next-instruction', 'step-instruction', 'interrupt']
    return sort(filter(l:exec_subcommand, 'stridx(v:val, a:arglead) == 0'))
endfunction

function! s:gdbnotify(event, ...) abort
    if !exists('g:gdbmi#_channel_id')
        " throw '[gdbmi]: channel id not defined!'
        GdbmiInitializePython
    endif
    call rpcnotify(g:gdbmi#_channel_id, a:event, a:000)
endfunction

function! gdbmi#util#define_commands() abort "{{{
    nnoremap <silent> <Plug>GDBBreakSwitch
                \ :call <SID>gdbnotify("breakswitch", expand("%:p"), line('.'))<CR>

    nnoremap <silent> <Plug>GDBBreakProperty
                \ :call <SID>gdbnotify("bkpt_property", expand("%:p"), line('.'))<CR>

    command!      -nargs=*    -complete=customlist,<SID>gdb_launch_complete
                \ GDBLaunch          call <SID>gdbnotify("launchgdb", <f-args>)

    command!      -nargs=+    -complete=customlist,<SID>gdb_exec_complete
                \ GDBExec          call <SID>gdbnotify("exec", <f-args>)

    command!     GDBQuit     call <SID>gdbnotify("quitgdb")

    nnoremap <silent> <Plug>GDBRuntoCursor
                \ :call <SID>gdbnotify("exec", "runtocursor", expand("%:p"), line('.'))<CR>

    vnoremap <silent> <Plug>GDBStdinSelected
            \ :<C-U>call <SID>gdbnotify("inferior_stdin", gdbmi#util#get_selection())<CR>

    nnoremap <silent> <Plug>GDBStdinPrompt
            \ :<C-U>call <SID>gdbnotify("inferior_stdin")<CR>

    nnoremap <silent> <Plug>GDBBreakModify
                \ :call <SID>gdbnotify("bkpt_modify")<CR>

endfunction
"}}}


