# encoding: utf-8

import re
import collections
from ast import literal_eval
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


TOKEN_NUM = r'(?P<TOKEN_NUM>^\d+)'
RESULT_CLASS = r'\^(?P<RESULT_CLASS>(done|running|connected|error|exit))'
EXEC_CLASS = r'\*(?P<EXEC_CLASS>[\w-]+)'
STATUS_CLASS = r'\+(?P<STATUS_CLASS>[\w-]+)'
NOTIFY_CLASS = r'=(?P<NOTIFY_CLASS>[\w-]+)'
CONSOLE_OUTPUT = r'^~\"(?P<CONSOLE_OUTPUT>((?:\\.|.)*?))\"(?=\n)'
TARGET_OUTPUT = r'^@\"(?P<TARGET_OUTPUT>((?:\\.|.)*?))\"(?=\n)'
LOG_OUTPUT = r'^&\"(?P<LOG_OUTPUT>((?:\\.|.)*?))\"(?=\n)'
L_TUPLE = r'(?P<L_TUPLE>\{)'
R_TUPLE = r'(?P<R_TUPLE>\})'
#  TUPLE = r'\{(?P<TUPLE>(.*))\}'
L_LIST = r'(?P<L_LIST>\[)'
R_LIST = r'(?P<R_LIST>\])'
#  LIST = r'\[(?P<LIST>(.*?))\]'
VARIABLE = r'(?P<VARIABLE>[\w-]+)='
CONST = r'\"(?P<CONST>((?:\\.|.)*?))\"'
GDB = r'(?P<GDB>\(gdb\))'
COMMA = r'(?P<COMMA>\,)'
NL = r'(?P<NL>\n)'
ASSIGN = r'(?P<ASSIGN>=)'


master_pat = re.compile(
    '|'.join(
        [
            TOKEN_NUM,
            RESULT_CLASS,
            EXEC_CLASS,
            STATUS_CLASS,
            NOTIFY_CLASS,
            CONSOLE_OUTPUT,
            TARGET_OUTPUT,
            LOG_OUTPUT,
            L_TUPLE,
            R_TUPLE,
            L_LIST,
            R_LIST,
            #  TUPLE, LIST,
            VARIABLE,
            CONST,
            GDB,
            COMMA,
            NL,
            ASSIGN,
        ]
    )
)

Token = collections.namedtuple('Token', ['type', 'value'])
ResultRecord = collections.namedtuple('ResultRecord', ['What', 'result_class', 'results'])
AsyncRecord = collections.namedtuple('AsyncRecord', ['What', 'async_class', 'name', 'results'])
StreamRecord = collections.namedtuple('StreamRecord', ['What', 'stream_class', 'output'])


class ParseError(Exception):
    pass


class GDBOutputParse:
    def __init__(self):
        self.debug, self.info, self.warn, self.error = (
            logger.debug,
            logger.info,
            logger.warn,
            logger.error,
        )
        self.GDB_PROMPT = object()
        self.record_parse_func = {
            'RESULT_CLASS': self.result_record,
            'EXEC_CLASS': self.async_record,
            'STATUS_CLASS': self.async_record,
            'NOTIFY_CLASS': self.async_record,
            'CONSOLE_OUTPUT': self.stream_record,
            'TARGET_OUTPUT': self.stream_record,
            'LOG_OUTPUT': self.stream_record,
        }
        self.string_parser = literal_eval

    @staticmethod
    def generate_tokens(text):
        #  scanner = master_pat.scanner(text)
        for m in master_pat.finditer(text):
            tok = Token(m.lastgroup, m.group(m.lastgroup))
            yield tok

    def parse(self, text):
        self.tokens = GDBOutputParse.generate_tokens(text)
        self.tok = None  # Last symbol consumed
        self.nexttok = None  # Next symbol tokenized
        self._advance()

        return self.output_parse()

    def output_parse(self):
        if self._accept('GDB'):
            return None, self.GDB_PROMPT

        n = self.token_num()
        return n, self.record_parse()

    def token_num(self):
        if self._accept('TOKEN_NUM'):
            return self.tok.value
        else:
            return None

    def record_parse(self):
        for c, f in self.record_parse_func.items():
            if self._accept(c):
                return f()

    def results(self):
        results = {}

        while self._accept("COMMA"):
            var, value = self.result()
            if var:
                results[var] = value
            elif len(results) == 1:
                k, v = results.popitem()
                if isinstance(v, list):
                    v.append(value)
                    results[k] = v
                else:
                    results[k] = [v, value]
            else:
                raise ParseError(repr(value))

        return results

    def result(self):
        if self._accept("VARIABLE"):
            var = self.tok.value
        elif self._test("L_TUPLE"):
            var = None
        else:
            raise ParseError(repr(self.tok) + repr(self.nexttok))

        value = self.value()

        return var, value

    def tuple(self):
        results = {}
        if self._accept("R_TUPLE"):
            return results

        var, value = self.result()
        results[var] = value

        while not self._accept("R_TUPLE"):
            if self._accept("COMMA"):
                var, value = self.result()
                results[var] = value
            else:
                raise ParseError(self.tok)

        return results

    def list(self):
        values = []
        if self._accept("R_LIST"):
            return values

        try:
            value = self.value()
            values.append(value)
        except ParseError:
            var, value = self.result()
            values.append(value)

            while not self._accept("R_LIST"):
                if self._accept("COMMA"):
                    var, value = self.result()
                    values.append(value)
                else:
                    raise ParseError(self.tok)
        else:
            while not self._accept("R_LIST"):
                if self._accept("COMMA"):
                    value = self.value()
                    values.append(value)
                else:
                    raise ParseError(self.tok)

        return values

    def value(self):
        if self._accept("L_TUPLE"):
            value = self.tuple()
        elif self._accept("L_LIST"):
            value = self.list()
        elif self._accept("CONST"):
            value = self.tok.value
        else:
            raise ParseError(self.tok)

        return value

    def result_record(self):
        result_class = self.tok.value
        results = self.results()
        if self._accept('NL'):
            return ResultRecord('ResultRecord', result_class, results)
        else:
            raise ParseError(repr(self.nexttok))

    def async_record(self):
        async_class = self.tok.type
        async_name = self.tok.value
        results = self.results()
        if self._accept('NL'):
            return AsyncRecord('AsyncRecord', async_class, async_name, results)
        else:
            raise ParseError(repr(self.tok) + repr(self.nexttok))

    def stream_record(self):
        stream_class = self.tok.type
        try:
            output = self.string_parser('"' + self.tok.value + '"')
        except SyntaxError:
            raise ParseError(repr(self.tok))

        #  if self.nexttok is None:
        if self._accept('NL'):
            return StreamRecord('StreamRecord', stream_class, output)
        else:
            raise ParseError(repr(self.nexttok))

    def _advance(self):
        self.tok, self.nexttok = self.nexttok, next(self.tokens, None)
        self.debug(repr(self.tok))

    def _accept(self, toktype):
        if self.nexttok and self.nexttok.type == toktype:
            self._advance()
            return True
        else:
            return False

    def _test(self, toktype):
        return self.nexttok.type == toktype


def test(output):
    parser = GDBOutputParse()
    result = parser.parse((output))
    print(result)
    return result


def main(filename):
    parser = GDBOutputParse()
    with open(filename) as f:
        for s in f:
            #  s = s.strip()
            print(">>" + s.strip())
            #  for t in generate_tokens(s):
            #      print("  " + repr(t))
            print("  " + repr(parser.parse(s)))


if __name__ == "__main__":
    #  import sys
    #  for tok in GDBOutputParse.generate_tokens(output):
    #      print(tok)
    test1 = (
        r'*stopped,reason="end-stepping-range",'
        + r'frame={addr="0x000000000040056e",func="seqsum",args=[{name="n",value="1000000"}],'
        + r'file="ab.c",fullname="gdbmi.nvim/test/ab.c",line="4"},thread-id="1",stopped-threads="all",core="2"'
        + '\n'
    )
    test2 = (
        r'0005^done,threads=[{id="1",target-id="process 12398",name="test_gdbmi",'
        + r'frame={level="0",addr="0x00000000004005c8",func="main",args=[],file="ab.c",fullname="gdbmi.nvim/test/ab.c",line="21"},'
        + r'state="stopped",core="1"}],current-thread-id="1"'
        + '\n'
    )
    test3 = (
        r'*stopped,reason="end-stepping-range",'
        + r'frame={addr="0x0000000000411e80",func="callParallel_calculate",args=[{name="outputFilePath",value="\"./temp_data_www_2.dat\""},{name="save_png",value="true"}],'
        + r'file="a.cpp",fullname="ab.cpp",line="326"},thread-id="1",stopped-threads="all",core="0"'
        + '\n'
    )
    test4 = (
        r'=breakpoint-created,bkpt={number="1",type="breakpoint",disp="keep",enabled="y",addr="<MULTIPLE>",times="0",original-location="fun"},'
        + r'{number="1.1",enabled="y",addr="0x000000000a1b7fa1",func="fun()",'
        + r'file="file1.c",fullname="file1.c",line="7048",thread-groups=["i1"]},'
        + r'{number="1.2",enabled="y",addr="0x000000000a1b96e8",func="fun()",'
        + r'file="file2.c",fullname="file2.c",line="7271",thread-groups=["i1"]},'
        + r'{number="1.3",enabled="y",addr="0x00002b07f6e52c40",at="<fun()@plt>",thread-groups=["i1"]}'
        + '\n'
    )
    test5 = (
        r'=breakpoint-created,bkpt={number="2",type="breakpoint",disp="keep",enabled="y",addr="<MULTIPLE>",times="0",original-location="seqsum",'
        + r'locations=[{number="2.1",enabled="y",addr="0x000000000040115e",func="seqsum(long)",file="ab.cpp",fullname="gdbmi.nvim/test/ab.cpp",line="5",thread-groups=["i1"]},'
        + r'{number="2.2",enabled="y",addr="0x00000000004011d6",func="seqsum(long, long)",file="ab.cpp",fullname="gdbmi.nvim/test/ab.cpp",line="21",thread-groups=["i1"]}]}'
        + '\r\n'
    )
    #  main(sys.argv[1])
    test(test1)
    test(test2)
    test(test3)
    test(test4)
    test(test5)
