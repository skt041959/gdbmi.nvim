import sys
import logging
from time import sleep
sys.path.insert(0, '../rplugin/python3/gdbmi_interface')

from gdbmi.session import Session

def main():
    logging.basicConfig(
        #level=logging.INFO,
        level=logging.DEBUG,
        format='%(asctime)s '\
            '%(levelname)s '\
            '%(pathname)s:%(lineno)s '\
            '%(message)s')

    logger = logging.getLogger(__name__)

    session = Session("./ab", output="/dev/pts/7")

    session.do_breakswitch(filename='ab.c', line=18)

if __name__ == '__main__':
    main()
