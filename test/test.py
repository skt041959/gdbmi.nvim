import sys
import logging
from time import sleep
sys.path.insert(0, '../rplugin/python3/gdbmi_interface')

import neovim

import gdbmi

def callback(*args):
    print("callback", args)

def main(vim):
    logging.basicConfig(
        #level=logging.INFO,
        level=logging.DEBUG,
        format='%(asctime)s '\
            '%(levelname)s '\
            '%(pathname)s:%(lineno)s '\
            '%(message)s')

    logger = logging.getLogger(__name__)

    session = gdbmi.Session(vim, "./test_gdbmi")

    session.do_breakswitch(filename='ab.c', line=18)

    session.do_exec('run', callback=callback)
    session.do_exec('next')
    session.do_exec('next')
    session.do_exec('next')
    session.do_exec('step')

    for line in sys.stdin:
        if line.startswith('-'):
            session.send_cmd(line.strip())
        else:
            session.send_console_cmd(line.strip())

    session.quit()

if __name__ == '__main__':

    vim = neovim.attach('child', argv=["/bin/env", "nvim", "--embed", "-u", "init.vim"])
    main(vim)
