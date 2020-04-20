
if exists('g:loaded_gdbmi')
    finish
endif
let g:loaded_gdbmi = 1

let s:bp_symbol = get(g:, 'gdbmi#sign#bp_symbol', 'B>')
let s:pc_symbol = get(g:, 'gdbmi#sign#pc_symbol', '->')

highlight default link GDBMIBreakpointSign Type
highlight default link GDBMIUnselectedPCSign NonText
highlight default link GDBMIUnselectedPCLine DiffChange
highlight default link GDBMISelectedPCSign Debug
highlight default link GDBMISelectedPCLine Visual

execute 'sign define GdbmiBreakpoint text=' . s:bp_symbol .
    \ ' texthl=GDBMIBreakpointSign linehl=GDBMIBreakpointLine'

execute 'sign define GdbmiCurrentLine text=' . s:pc_symbol .
    \ ' texthl=GDBMISelectedPCSign linehl=GDBMISelectedPCLine'

execute 'sign define GdbmiCurrentLine2 text=' . s:pc_symbol .
    \ ' texthl=GDBMIUnselectedPCSign linehl=GDBMIUnselectedPCLine'

command! -nargs=1 -complete=shellcmd GDBMILaunch call gdbmi#init#Spawn(<q-args>)

let g:gdbmi_split_direction = get(g:, 'gdbmi_split_direction', 'h')
let g:gdbmi_delete_after_quit = get(g:, 'gdbmi_delete_after_quit', 0)

