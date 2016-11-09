
let g:gdbmi#auto_mapping = 0
let g:gdbmi#auto_initialize = 0

function! gdbmi#init#enable() abort "{{{
endfunction "}}}

function! gdbmi#init#createWindow() abort "{{{
    vsplit term://zsh
    setlocal bufhidden=hide
    let g:gdbmi#_terminal_job_pid = b:terminal_job_pid
    let g:gdbmi#_terminal_job_id = b:terminal_job_id
    wincmd L
    wincmd h
endfunction "}}}
