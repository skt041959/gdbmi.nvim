import os
import logging
import traceback
import inspect
import sys


logger = logging.getLogger("gdbmi")

log_format = '%(asctime)s %(levelname)-8s [%(process)d] (%(name)s) %(message)s'
formatter = logging.Formatter(log_format)
handler = logging.FileHandler(filename="/tmp/gdbmi_log")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def getLogger(name):
    return logger.getChild(name)


def exception(logger):
    """
    A decorator that wraps the passed in function and logs
    exceptions should one occur

    @param logger: The logging object
    """

    def decorator(func):

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                # log the exception
                err = "There was an exception in  "
                err += func.__name__
                logger.exception(err)

                # re-raise the exception
                raise
        return wrapper
    return decorator


LOG_FRAME_TPL = '  File "%s", line %i, in %s\n    %s\n'

# log_exceptions decorator
def log_exceptions(logger,
                   frame_template = LOG_FRAME_TPL,
                   log_if = True):
    """
    A decorator that catches any exceptions thrown by the decorated function and
    logs them along with a traceback that includes every local variable of every
    frame.

    Notes:
        Caught exceptions are re-raised.
    Args:
        log_file_name (string): a path to the log file. Defaults to
                                'exceptions.log'.
        frame_template (string): a format string used to format frame information.
                                The following format arguments will be used when
                                printing a frame:
                                 * (string) The name of the file the frame belongs
                                            to.
                                 * (int) The line number on which the frame was
                                         created.
                                 * (string) The name of the function the frame
                                            belongs to.
                                 * (string) The python code of the line where the
                                            frame was created.
                                The default frame template outputs frame info as
                                it appears in normal python tracebacks.
        log_if (bool): a flag that can disable logging. This argument can be used
                       to disable/enable logging in specific situations. For
                       example, it can be set to the result of:

                       os.getenv('MYAPP_DEBUG') is not None

                       to make sure logging is only performed when the MYAPP_DEBUG
                       environment variable is defined.
    Returns:
        A decorator that catches and logs exceptions thrown by decorated functions.
    Raises:
        Nothing. The decorator will re-raise any exception caught by the decorated
        function.
    """

    def decorator(func):
        def wrapper(*args, **kwds):
            # this variable is never used. it exists so we can detect if a frame is
            # referencing this specific function.
            __lgw_marker_local__ = 0

            try:
                return func(*args, **kwds)
            except Exception as e:
                if not log_if:
                    raise

                log_lines = ""
                try:
                    # log exception information first in case something fails below
                    log_lines += "Exception thrown, {}: {}\n".format(type(e), e)

                    # iterate through the frames in reverse order so we print the
                    # most recent frame first
                    frames = inspect.getinnerframes(sys.exc_info()[2])
                    for frame_info in reversed(frames):
                        f_locals = frame_info[0].f_locals

                        # if there's a local variable named __lgw_marker_local__, we assume
                        # the frame is from a call of this function, 'wrapper', and we skip
                        # it. Printing these frames won't help determine the cause of an
                        # exception, so skipping it reduces clutter.
                        #  if '__lgw_marker_local__' in f_locals:
                        #      continue

                        # log the frame information
                        log_lines += frame_template % (frame_info[1], frame_info[2], frame_info[3], frame_info[4][0].lstrip())

                        # log every local variable of the frame
                        #  for k, v in f_locals.items():
                        #      log_lines += "%s = %r\n" % (k, v)
                    log_lines += "\n"
                finally:
                    logger.debug(log_lines)

                raise
        return wrapper
    return decorator

