
if exists('g:loaded_gdbmi') || !has('nvim') || !has('python')
    finish
endif

let g:loaded_gdbmi = 1

let s:bp_symbol = get(g:, 'gdbmi#sign#bp_symbol', 'B>')
let s:pc_symbol = get(g:, 'gdbmi#sign#pc_symbol', '->')

highlight default link GDBBreakpointSign Type
highlight default link GDBUnselectedPCSign NonText
highlight default link GDBUnselectedPCLine DiffChange
highlight default link GDBSelectedPCSign Debug
highlight default link GDBSelectedPCLine DiffText

execute 'sign define GdbmiBreakpoint text=' . s:bp_symbol .
    \ ' texthl=GDBBreakpointSign linehl=GDBBreakpointLine'

execute 'sign define GdbmiCurrentLine text=' . s:pc_symbol .
    \ ' texthl=GDBSelectedPCSign linehl=GDBSelectedPCLine'

" execute 'sign define gdbsign_pcunsel text=' . s:pc_symbol .
"     \ ' texthl=GDBUnselectedPCSign linehl=GDBUnselectedPCLine'

call gdbmi#util#define_commands()

command! -nargs=1 -complete=shellcmd GDBLaunch call gdbmi#init#Spawn(<q-args>)
