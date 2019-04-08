
let g:gdbmi#auto_mapping = 0


function! gdbmi#init#Spawn(cmd) abort

  sp | wincmd T

  call gdbmi#util#util_init()

  let l:tty = _gdbmi_start()

  let l:cmd = a:cmd .' -ex "new-ui mi '. l:tty .'"'

  sp | wincmd j | enew | let t:gdbmi_gdb_buf = termopen(l:cmd)

  startinsert

endfunction
