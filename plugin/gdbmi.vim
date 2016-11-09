
if exists('g:loaded_gdbmi') || !has('nvim') || !has('python')
    finish
endif

let g:loaded_gdbmi = 1

if !exists('g:gdbmi#init#gdb')
    let g:gdbmi#init#gdb = 'gdb'
endif
if !exists('g:gdbmi#session#file')
    let g:gdbmi#session#file = 'gdbmi-nvim.json'
endif
if !exists('g:gdbmi#session#mode_setup')
    let g:gdbmi#session#mode_setup = 'gdbmi#layout#setup'
endif
if !exists('g:gdbmi#session#mode_teardown')
    let g:gdbmi#session#mode_teardown = 'gdbmi#layout#teardown'
endif

let s:bp_symbol = get(g:, 'gdbmi#sign#bp_symbol', 'B>')
let s:pc_symbol = get(g:, 'gdbmi#sign#pc_symbol', '->')

highlight default link GDBBreakpointSign Type
highlight default link GDBUnselectedPCSign NonText
highlight default link GDBUnselectedPCLine DiffChange
highlight default link GDBSelectedPCSign Debug
highlight default link GDBSelectedPCLine DiffText

execute 'sign define gdbsign_bpres text=' . s:bp_symbol .
    \ ' texthl=GDBBreakpointSign linehl=GDBBreakpointLine'

execute 'sign define gdbsign_pcsel text=' . s:pc_symbol .
    \ ' texthl=GDBSelectedPCSign linehl=GDBSelectedPCLine'

execute 'sign define gdbsign_pcunsel text=' . s:pc_symbol .
    \ ' texthl=GDBUnselectedPCSign linehl=GDBUnselectedPCLine'

call gdbmi#util#define_commands()

if g:gdbmi#auto_mapping
    nmap <leader>br <Plug>GDBBreakSwitch
    nnoremap <F8> :GDBExec continue<CR>
    nnoremap <F9> :GDBExec next<CR>
    nnoremap <F10> :GDBExec step<CR>
    nnoremap <F5> :GDBExec run<CR>
    nnoremap <F11> :GDBExec interrupt<CR>
endif

if g:gdbmi#auto_initialize
    GdbmiInitializePython
endif

