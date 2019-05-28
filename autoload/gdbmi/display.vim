let g:gdbmi_float_window = -1
let g:gdbmi_float_window_bufs = {}

let s:float_opts = {
      \ 'relative': 'editor',
      \ 'width': 0,
      \ 'width_percent': 80,
      \ 'height': 0,
      \ 'height_percent': 80,
      \ 'col': 0,
      \ 'row': 1,
      \ 'anchor': 'NW',
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
  let l:buf = get(g:gdbmi_float_window_bufs, a:context['type'], -1)
  if l:buf < 0
    let g:gdbmi_float_window_bufs[a:context['type']] = nvim_create_buf(v:false, v:true)
    let l:buf = get(g:gdbmi_float_window_bufs, a:context['type'], -1)
  endif

  let content = a:context['content']
  call extend(content, ['', '=================================', ''])

  let linenr = nvim_buf_line_count(l:buf)

  call nvim_buf_set_lines(l:buf, linenr, -1, v:true, content)

  let linenr = nvim_buf_line_count(l:buf)

  call nvim_buf_add_highlight(l:buf, -1, 'String', linenr-2, 0, -1)

  let t:gdbmi_float_window_opts['width'] = &columns * s:float_opts['width_percent'] / 100
  let t:gdbmi_float_window_opts['height'] = &lines * s:float_opts['height_percent'] / 100

  exe 'augroup GDBMI_BUF_' . l:buf . ' | augroup END'
  nnoremap <esc> :call gdbmi#display#close_float()<CR>

  let g:gdbmi_float_window = nvim_open_win(l:buf, 1, t:gdbmi_float_window_opts)
endfunction

function! gdbmi#display#close_float() abort
  if g:gdbmi_float_window < 0
    return
  endif

  call nvim_win_close(g:gdbmi_float_window, 1)
  let g:gdbmi_float_window = -1
endfunction
