#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
from pyparsing import *
from base64 import b64decode
import util

class OtrPrivateKeys():

    @staticmethod
    def verifyLen(t):
        t = t[0]
        if t.len is not None:
            t1len = len(t[1])
            if t1len != t.len:
                raise ParseFatalException, \
                        "invalid data of length %d, expected %s" % (t1len, t.len)
        return t[1]

    @staticmethod
    def parse_sexp(data):
        '''parse sexp/S-expression format and return a python list'''
        # define punctuation literals
        LPAR, RPAR, LBRK, RBRK, LBRC, RBRC, VBAR = map(Suppress, "()[]{}|")

        decimal = Word("123456789",nums).setParseAction(lambda t: int(t[0]))
        bytes = Word(printables)
        raw = Group(decimal.setResultsName("len") + Suppress(":") + bytes).setParseAction(OtrPrivateKeys.verifyLen)
        token = Word(alphanums + "-./_:*+=")
        base64_ = Group(Optional(decimal,default=None).setResultsName("len") + VBAR
            + OneOrMore(Word( alphanums +"+/=" )).setParseAction(lambda t: b64decode("".join(t)))
            + VBAR).setParseAction(OtrPrivateKeys.verifyLen)

        hexadecimal = ("#" + OneOrMore(Word(hexnums)) + "#")\
                        .setParseAction(lambda t: int("".join(t[1:-1]),16))
        qString = Group(Optional(decimal,default=None).setResultsName("len") +
                                dblQuotedString.setParseAction(removeQuotes)).setParseAction(OtrPrivateKeys.verifyLen)
        simpleString = raw | token | base64_ | hexadecimal | qString

        display = LBRK + simpleString + RBRK
        string_ = Optional(display) + simpleString

        sexp = Forward()
        sexpList = Group(LPAR + ZeroOrMore(sexp) + RPAR)
        sexp << ( string_ | sexpList )

        try:
            sexpr = sexp.parseString(data)
            return sexpr.asList()[0][1:]
        except ParseFatalException, pfe:
            print("Error:", pfe.msg)
            print(line(pfe.loc,t))
            print(pfe.markInputline())

    @staticmethod
    def parse(filename):
        '''parse the otr.private_key S-Expression and return an OTR dict'''

        f = open(filename, 'r')
        data = ""
        for line in f.readlines():
            data += line
        f.close()

        sexplist = OtrPrivateKeys.parse_sexp(data)
        keydict = dict()
        for sexpkey in sexplist:
            if sexpkey[0] == "account":
                key = dict()
                name = ''
                for element in sexpkey:
                    # 'name' must be the first element in the sexp or BOOM!
                    if element[0] == "name":
                        if element[1].find('/') > -1:
                            name, resource = element[1].split('/')
                        else:
                            name = element[1].strip()
                            resource = ''
                        key = dict()
                        key['name'] = name.strip()
                        key['resource'] = resource.strip()
                    if element[0] == "protocol":
                        key['protocol'] = element[1]
                    elif element[0] == "private-key":
                        if element[1][0] == 'dsa':
                            key['type'] = 'dsa';
                            for num in element[1][1:6]:
                                key[num[0]] = num[1]
                keytuple = (key['y'], key['g'], key['p'], key['q'])
                key['fingerprint'] = util.fingerprint(keytuple)
                keydict[name] = key
        return keydict


    @staticmethod
    def write(keydict, filename):
        privkeys = '(privkeys\n'
        for name, key in keydict.items():
            if 'x' in key:
                dsa = '  (p #' + ('%0258X' % key['p']) + '#)\n'
                dsa += '  (q #' + ('%042X' % key['q']) + '#)\n'
                dsa += '  (g #' + ('%0258X' % key['g']) + '#)\n'
                dsa += '  (y #' + ('%0256X' % key['y']) + '#)\n'
                dsa += '  (x #' + ('%042X' % key['x']) + '#)\n'
                contents = ('(name "' + key['name'] + '")\n' +
                             '(protocol ' + key['protocol'] + ')\n' +
                             '(private-key \n (dsa \n' + dsa + '  )\n )\n')
                privkeys += ' (account\n' + contents + ' )\n'
        privkeys += ')\n'
        f = open(filename, 'w')
        f.write(privkeys)
        f.close()

if __name__ == "__main__":
    import sys
    import pprint

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(OtrPrivateKeys.parse(sys.argv[1]))
