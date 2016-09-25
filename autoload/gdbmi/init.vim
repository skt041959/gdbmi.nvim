
function! gdbmi#init#enable() abort "{{{
endfunction "}}}

function! gdbmi#init#createWindow() abort "{{{
    vsplit term://zsh
    let g:gdbmi#_terminal_job_pid = b:terminal_job_pid
    wincmd L
    wincmd h
endfunction "}}}
