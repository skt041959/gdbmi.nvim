
let g:gdbmi#auto_mapping = 0


function! gdbmi#init#Spawn(cmd) abort
  let t:gdbmi_win_jump_window = 1
  let t:gdbmi_win_current_buf = -1

  let t:gdbmi_cursor_line = -1
  let t:gdbmi_cursor_sign_id = -1

  let l:tty = _gdbmi_start()

  let l:cmd = a:cmd .' -ix "new-ui '. l:tty .'"'
  tabnew | sp | wincmd j | enew | let t:gdbmi_gdb_buf = termopen(a:cmd)

endfunction
