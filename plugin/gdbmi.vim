
command! -nargs=1 -complete=shellcmd GDBMILaunch           call gdbmi#init#Spawn(<q-args>, <q-mods>, 'no')
command! -nargs=1 -complete=shellcmd GDBMILaunchNewTTY     call gdbmi#init#Spawn(<q-args>, <q-mods>, 'show')
command! -nargs=1 -complete=shellcmd GDBMILaunchHideNewTTY call gdbmi#init#Spawn(<q-args>, <q-mods>, 'hide')

let g:gdbmi_delete_after_quit = get(g:, 'gdbmi_delete_after_quit', 0)
let g:gdbmi_disable_autoread = get(g:, 'gdbmi_disable_autoread', 1)

