
# encoding: utf-8

import re
import collections

TOKEN_NUM = r'(?P<TOKEN_NUM>^\d+)'
RESULT_CLASS = r'\^(?P<RESULT_CLASS>(done|running|connected|error|exit))'
EXEC_CLASS = r'\*(?P<EXEC_CLASS>[\w-]+)'
STATUS_CLASS = r'\+(?P<STATUS_CLASS>[\w-]+)'
NOTIFY_CLASS = r'=(?P<NOTIFY_CLASS>[\w-]+)'
CONSOLE_OUTPUT = r'^~\"(?P<CONSOLE_OUTPUT>(.*?))\"'
TARGET_OUTPUT = r'^@\"(?P<TARGET_OUTPUT>(.*?))\"'
LOG_OUTPUT = r'^&\"(?P<LOG_OUTPUT>(.*?))\"'
# L_TUPLE = r'(?P<L_TUPLE>\{)'
# R_TUPLE = r'(?P<R_TUPLE>\})'
TUPLE = r'\{(?P<TUPLE>(.*?))\}'
# L_LIST = r'(?P<L_LIST>\[)'
# R_LIST = r'(?P<R_LIST>\])'
LIST = r'\[(?P<LIST>(.*?))\]'
VARIABLE = r'(?P<VARIABLE>[\w-]+)='
CONST = r'\"(?P<CONST>(.*?))\"'
GDB = r'(?P<GDB>\(gdb\))'
COMMA = r'(?P<COMMA>\,)'
NL = r'(?P<NL>\n)'
ASSIGN = r'(?P<ASSIGN>=)'


master_pat = re.compile('|'.join([TOKEN_NUM, RESULT_CLASS,
                                  EXEC_CLASS, STATUS_CLASS, NOTIFY_CLASS,
                                  CONSOLE_OUTPUT, TARGET_OUTPUT, LOG_OUTPUT,
                                  # L_TUPLE, R_TUPLE,
                                  # L_LIST, R_LIST,
                                  TUPLE, LIST,
                                  VARIABLE, CONST,
                                  GDB, COMMA, NL, ASSIGN,
                                  ])
                        )

Token = collections.namedtuple('Token', ['type', 'value'])
ResultRecord = collections.namedtuple('ResultRecord', ['result_class', 'results'])
AsyncRecord = collections.namedtuple('AsyncRecord', ['async_class', 'name', 'results'])
StreamRecord = collections.namedtuple('StreamRecord', ['stream_class', 'output'])


def generate_tokens(text):
    #  scanner = master_pat.scanner(text)
    for m in master_pat.finditer(text):
        tok = Token(m.lastgroup, m.group(m.lastgroup))
        yield tok

GDB_PROMPT = object()

class ParseError(Exception):
    pass


class GDBOutputParse:

    def __init__(self):
        self.record_parse_func = {'RESULT_CLASS' : self.result_record,
                                'EXEC_CLASS' : self.async_record,
                                'STATUS_CLASS' : self.async_record,
                                'NOTIFY_CLASS' : self.async_record,
                                'CONSOLE_OUTPUT' : self.stream_record,
                                'TARGET_OUTPUT' : self.stream_record,
                                'LOG_OUTPUT' : self.stream_record
                                }

    def parse(self, text):
        self.tokens = generate_tokens(text)
        self.tok = None # Last symbol consumed
        self.nexttok = None  # Next symbol tokenized
        self._advance()
        return self.output_parse()

    def output_parse(self):
        if self._accept('GDB'):
            return GDB_PROMPT

        n = self.token_num()
        return n, self.record_parse()

    def token_num(self):
        if self._accept('TOKEN_NUM'):
            return int(self.tok.value)
        else:
            return None

    def record_parse(self):
        for c, f in self.record_parse_func.items():
            if self._accept(c):
                return f()

    def results(self):
        value_pat = re.compile('|'.join([r'\{(?P<T>(.*?))\}',
                                         r'\[(?P<L>(.*?))\]',
                                         r'(?P<V>[\w-]+)=',
                                         r'\"(?P<C>(.*?))\"',
                                         r'(?P<A>\,)',
                                         ]))
        def tuple_parse(seq):
            value_iter = value_pat.finditer(seq)
            results = {}
            while 1:
                m = next(value_iter, None)
                if m is None:
                    break
                kind = m.lastgroup
                value = m.group(kind)
                if kind == 'V':
                    var = value
                    m = next(value_iter, None)
                    if m is None:
                        raise ParseError
                    kind = m.lastgroup
                    if kind == 'T':
                        value = tuple_parse(m.group(kind))
                    elif kind == 'L':
                        value = [e.strip()[1:-1] for e in m.group(kind).split(',')]
                    elif kind == 'C':
                        value = m.group(kind)
                    else:
                        raise ParseError
                    results[var] = value
                    m = next(value_iter, None)
                    if m is None:
                        break
                    elif m.lastgroup == 'A':
                        continue
                    else:
                        raise ParseError
                else:
                    raise ParseError
            return results

        results = {}
        while self._accept("COMMA"):
            if self._accept("VARIABLE"):
                var = self.tok.value
            if self._accept("TUPLE"):
                value = tuple_parse(self.tok.value)
            elif self._accept("LIST"):
                value = [e.strip()[1:-1] for e in self.tok.value.split(',')]
            elif self._accept("CONST"):
                value = self.tok.value
            try:
                results[var] = value
            except:
                raise ParseError
        return results

    def result_record(self):
        result_class = self.tok.value
        results = self.results()
        return ResultRecord(result_class, results)

    def async_record(self):
        async_class = self.tok.type
        async_name = self.tok.value
        results = self.results()
        return AsyncRecord(async_class, async_name, results)

    def stream_record(self):
        stream_class = self.tok.type
        output = self.tok.value
        return StreamRecord(stream_class, output)

    def _advance(self):
        self.tok, self.nexttok = self.nexttok, next(self.tokens, None)

    def _accept(self, toktype):
        if self.nexttok and self.nexttok.type == toktype:
            self._advance()
            return True
        else:
            return False


def main():
    parser = GDBOutputParse()
    with open('./test.txt') as f:
        for s in f:
            s = s.strip()
            print(">>" + s)
            #  for t in generate_tokens(s):
            #      print("  " + repr(t))
            print("  " + repr(parser.parse(s)))


if __name__ == "__main__":
    main()

