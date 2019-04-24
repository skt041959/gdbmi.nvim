let g:gdbmi_float_window = -1
let g:gdbmi_float_window_buf = -1

let s:float_opts = {
      \ 'relative': 'editor',
      \ 'width': 0,
      \ 'width_percent': 80,
      \ 'height': 0,
      \ 'height_percent': 80,
      \ 'col': 0,
      \ 'row': 1,
      \ 'anchor': 'SE',
      \ }

function! gdbmi#display#init() abort
  let t:gdbmi_float_window_opts = copy(s:float_opts)

  if exists('g:gdbmi_float_window_opts_override')
    call extend(s:float_opts, g:gdbmi_float_window_opts_override)
    call extend(t:gdbmi_float_window_opts, g:gdbmi_float_window_opts_override)
  endif

  call remove(t:gdbmi_float_window_opts, 'width_percent')
  call remove(t:gdbmi_float_window_opts, 'height_percent')
endfunction

function! gdbmi#display#display(context) abort
  if g:gdbmi_float_window_buf < 0
    let g:gdbmi_float_window_buf = nvim_create_buf(v:false, v:true)
  endif

  let content = a:context['content']
  call extend(content, ['', '=================================', ''])

  let linenr = nvim_buf_line_count(g:gdbmi_float_window_buf)

  call nvim_buf_set_lines(g:gdbmi_float_window_buf, linenr, -1, v:true, content)

  let linenr = nvim_buf_line_count(g:gdbmi_float_window_buf)

  echo linenr

  call nvim_buf_add_highlight(g:gdbmi_float_window_buf, -1, 'String', linenr-1, 0, -1)

  let t:gdbmi_float_window_opts['width'] = &columns * s:float_opts['width_percent'] / 100
  let t:gdbmi_float_window_opts['height'] = &lines * s:float_opts['height_percent'] / 100

  let g:gdbmi_float_window = nvim_open_win(g:gdbmi_float_window_buf, 1, t:gdbmi_float_window_opts)
endfunction
