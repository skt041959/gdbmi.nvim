
if exists('g:loaded_gdbmi')
    finish
endif
let g:loaded_gdbmi = 1

command! -nargs=1 -complete=shellcmd GDBMILaunch call gdbmi#init#Spawn(<q-args>, <q-mods>, v:false)
command! -nargs=1 -complete=shellcmd GDBMILaunchNewTTY call gdbmi#init#Spawn(<q-args>, <q-mods>, v:true)

let g:gdbmi_delete_after_quit = get(g:, 'gdbmi_delete_after_quit', 0)

