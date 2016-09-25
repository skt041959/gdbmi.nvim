function gdbmi#util#print_error(msg) abort
    echohl Error | echomsg '[gdbmi]: ' . a:msg | echohl None
endfunction

function s:gdbcomplete(arg, line, pos)
    return []
endfunction

function! s:gdbnotify(event, ...) abort
    if !exists('g:gdbmi#_channel_id')
        throw 'GDB: channel id not defined!'
    endif
    call gdbmi#util#print_error(string(a:000))
    call rpcnotify(g:gdbmi#_channel_id, a:event, a:000)
endfun

function! gdbmi#util#define_commands() abort "{{{
    command!      -nargs=*    -complete=customlist,<SID>gdbcomplete
                \ GDBLaunch          call <SID>gdbnotify("launchgdb", <f-args>)
    "command!      -nargs=?    -complete=customlist,<SID>stdincompl
    "        \ LLstdin     call lldb#remote#stdin_prompt(<f-args>)

    "nnoremap <Plug>GDBBreakSwitch
    "            \ :call <SID>gdbnotify("breakswitch", bufnr("%"), getcurpos()[1])<CR>
    "vnoremap <silent> <Plug>LLStdInSelected
    "        \ :<C-U>call <SID>llnotify("stdin", lldb#util#get_selection())<CR>
    command! GDBBreakSwitch 
                \ call <SID>gdbnotify("breakswitch", expand("%:p"), getcurpos()[1])
endfunction
"}}}


