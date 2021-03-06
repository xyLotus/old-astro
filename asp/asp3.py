# python >= 3.6
""" This is the code parser for Astro Script Executable (.asx) files.
It is supposed to be used as a plug-in script, not being executed as
a standalone program. When using it as a module, just use the parse
function. This has no dependencies apart from the Python standard
library.

* asp3: The third asx code format (pax3) will probably be supported
  for quite some time, as it is the main parser ASX is based on, as of
  December, 2020. The previous version called just asp, has been deprecated
  as it was very buggy and had a lot problems and missing functionality.
  asp3 will hopefully fix these problems by implementing a new way and
  format for the asx code, so using it also becomes easier. Quick note:
  the __version__ of the parser is defined with 3 numbers: the first one
  represents the format, the second one shows the major version, and the
  third the minor version. If two implementations have the same format
  & major version, it is highly possible there should be no compatibility
  issues.

* Versions: This version will be supported as long as the interpreter will
  be using it, however parallel development of a new format can happen.
  This style of work has been chosen because creating a new, stable parser
  takes a lot of work and time, so in order to shorten the project development
  downtime to a minimum, an older version will be supported & bug-fixed
  while a fresh and new version is being worked on. Every new version of
  asp will be thoroughly tested before deployment, even if the beta is
  already committed to the Github repository.

* How it works: The main function of this whole parser would be the parse()
  function, taking in the lines of the script as a list of strings, and
  returning a JSON-serializable code object for the interpreter to read
  and execute. Internally, the parse() function creates an instance of the
  _Parser class to call its render() method which returns the generated code
  object (which happens already in the __init__ function. The constructor
  takes in the list of strings, cleaning them up, removing comments and
  calculating tab sizes. Note: a single tab can be any amount of spaces,
  but then it has to be kept the same for every single indent, or the
  parser will raise an IndentError which the interpreter can catch and
  read.

* Typing: After cleaning, each line of code is passed to the type() method,
  which defines the type and class of the code, using regular expression
  patterns. After that, each type is sent out to a different method returning
  the parsed line. You can easily tell such a method as its name starts with
  the 'parse_' prefix.

* Sorting: After typing, the lines are sorted and put into blocks depending
  on their indent size. All the different blocks can be found just scrolling
  down a bit and looking at the 'BLOCKS' constant, containing a list of
  block statement types.

* Shifting: After sorting, the lines and blocks are shifted to the final
  astro code compatible format from the parser-only internal format. The
  final result is the JSON-serializable code object represented as a list
  of statements (list of dicts).

"""
from asp import apt
import datetime
import re

__author__ = 'bellrise'
__version__ = '3.5.4'

# This is the format version of the code object generated
# by the parser, each new format is most probably incompatible
# with the older one, as names get changed and data shifted
# around or added into other containers. The current version
# is pax3, which stands for Parsed Astro Executable 3.
FORMAT = 'pax3'

# Blocks is a list of statement types which represent code
# blocks, that are executed depending on the conditions.
BLOCKS = ['if', 'else', 'elif', 'try', 'while', 'function']


class _Parser:
    # Internal class, do not use!

    OPT_HEADER_TITLE = '_HEADER'  # title of the header
    OPT_ASSIGNMENT_KW = 'data'  # the keyword used for the data field

    def __init__(self, lines: list, **kw):
        """ Entry point for the parser. """

        # Header title
        if kw.get('header_title'):
            if not isinstance(kw['header_title'], str):
                raise apt.ParserError('opt: invalid header_title type')
            self.OPT_HEADER_TITLE = kw['header_title']

        # Alternative assignment keyword option
        if kw.get('assignment_kw'):
            if not isinstance(kw['assignment_kw'], str):
                raise apt.ParserError('opt: invalid assignment_kw type')
            self.OPT_ASSIGNMENT_KW = kw['assignment_kw']

        # Execution
        self.code = [s.strip('\n') for s in lines]
        self.clean()
        self.tabsize = self.init_whitespace()
        self.count_whitespace()
        self.code = self.type(self.code)

    @staticmethod
    def hash_strings(line, num):
        """ Replaces all strings with hashes for commenting
        purposes. """
        matches = re.finditer('"[^"]*"', line)
        for match in matches:
            if match:
                substr = line[match.start():match.end()]
                line = line.replace(substr, '#' * len(substr))
        if '"' in line:
            raise SyntaxError(f'Incorrect string formatting @ line {num}')
        return line

    def clean(self):
        """ Replaces all the comment lines with a double dash """
        in_comment = False
        commented = []

        # Multi line comments
        for index, line in enumerate(self.code):
            if in_comment:
                # In comment
                commented.append(index)

            if re.match('^/--', line.strip()):
                # Start of comment
                in_comment = True
                commented.append(index)

            if re.match('.*--/$', line.strip()):
                # End of comment
                if in_comment:
                    in_comment = False
                    commented.append(index)

        for i in commented:
            self.code[i] = ''

        # Single line comments
        for index, line in enumerate(self.code):
            modified: str = self.hash_strings(line, index)
            comment = modified.find('--')
            if comment != -1:
                chars = list(line)
                del chars[comment:]
                self.code[index] = ''.join(chars)

    def init_whitespace(self):
        """ Check the first occurring whitespace and return
        the basic whitespace amount. """
        for line in self.code:
            match = re.match(r'^ *', str(line))
            if match.end() != 0:
                return len(line[0:match.end()])
        return 4

    def count_whitespace(self):
        """ Take each line and present the tab size in an int. This also
        places a line number in each line, to keep track of the lines. """
        for index, line in enumerate(self.code):
            match = re.match(r'^ *', line)
            if match.end() == 0:
                self.code[index] = [index + 1, 0, line.strip()]
            # Size checking
            if match.end() % self.tabsize != 0:
                raise IndentationError(f'Invalid tab size @ line {index}')

            self.code[index] = [index + 1, int(match.end() / self.tabsize), line.strip()]

    def type(self, lines):
        """ This is the main function for setting the types of the
        statements and parsing them into valid ASX Parsed code format.
        This is called recursively because of the multiple functions. """

        in_func = False
        func_indent = 0
        func = []
        collected = []

        # Functions
        for pos, line in enumerate(lines):
            indent = line[1]
            text = line[2]

            # Functions
            if re.match(r'^#[_A-z][_A-z0-9]*\(.*\):', text) and not in_func:
                in_func = True
                func_indent = indent
                func.append(line)
                continue

            # Inside of function
            if in_func and (indent > func_indent) and text:
                func.append(line)
                continue

            # Outside of function
            if in_func and (indent <= func_indent):
                in_func = False
                func_indent = 0
                collected.append(func)
                func = []

        # Statements / function calls
        for pos, line in enumerate(lines):
            text = line[2]

            structures = {
                # Module import
                r'import .*': self.parse_import,

                # Delete keyword
                r'delete .*': self.parse_delete,

                # If block header
                r'^if .*:.*': self.parse_if,

                # While block header
                r'^while .+:.*': self.parse_while,

                # For loop header
                r'^for .+:.*': self.parse_for,

                # Elif block header
                r'^elif .*:.*': self.parse_elif,

                # Else block header
                r'^else:': self.parse_else,

                # Try block header
                r'^try:': self.parse_try,

                # Function block header
                r'^#[_A-z][_A-z0-9]*\(.*\):': self.parse_header,

                # Assignment statement
                r'^[_A-z][_A-z0-9]* *= *.*': self.parse_assignment,

                # Function call statement
                r'^[_A-z][_A-z0-9]*\(.*\)': self.parse_call,

                # Regular base statement
                r'^[_A-z][_A-z0-9]*.*': self.parse_statement,

                # Mixin
                r'^@mixin .*': self.parse_mixin,

            }

            unparsed = True
            for regex, method in structures.items():
                if re.match(regex, text):
                    lines[pos] = method(line)
                    unparsed = False
                    break

            if unparsed and line[2]:
                raise SyntaxError(f'Invalid syntax @ {line[0]}')

        # I have to add a phantom line or the whole indent sorter
        # will crash and burn and die and stop working, and this
        # is a lot easier then having to write a pusher which would
        # take another 30 lines. Trust me, I know what im doing.
        if lines:
            index = lines[-1][0] + 1
        else:
            index = 0
        lines.append([index, 0, ''])

        # Recursive sorting to reach every level of statements,
        # also turns the code object format to such one that the
        # interpreter can understand. This also removes all empty
        # lines that don't need to be interpreted.
        lines = self.recursive_sort(lines)

        return lines

    @staticmethod
    def format(code):
        """ Converts the parser format to a format that the interpreter
        understands. """
        b = {'line': code[0]}
        b.update(code[2])
        return b

    def recursive_sort(self, lines):
        """ Recursively calls sort_code_blocks for each 'code' field
        found in any line. """
        lines = self.sort_code_blocks(lines)

        master = []

        for index, line_ in enumerate(lines):
            index = line_[0]
            indent = line_[1]
            code = line_[2]

            # Empty code lines, not important
            if not code:
                continue

            if 'code' in code:
                code_ = self.recursive_sort(code['code'])
                b: dict = code
                b['code'] = code_
                new_block = [index, indent, b]
                master.append(self.format(new_block))
            else:
                master.append(self.format(line_))

        return master

    @staticmethod
    def sort_code_blocks(lines):
        """ Sorts the code blocks into separate blocks, depending
        on their indentation level. """
        new = lines.copy()

        map_ = []
        for i in new:
            map_.append(i[0])

        collected = []

        cursor = 0
        while cursor < len(lines) - 1:

            indent = new[cursor][1]
            code = new[cursor][2]

            if not code:
                cursor += 1
                continue

            block = []

            # Basically checks if the type of the statement
            # is a block type
            if code['type'] in BLOCKS:
                starting_indent = indent
                block_header = new[cursor]
                cursor += 1
                while True:
                    if cursor >= len(new):
                        break

                    if starting_indent != new[cursor][1]:
                        block.append(new[cursor])
                        collected.append(new[cursor][0])
                    else:
                        # Collect the statements into one pile
                        pulled = new[map_.index(block_header[0])]
                        d: dict = pulled[2]
                        d.update({'code': block})
                        new[map_.index(block_header[0])] = [pulled[0], pulled[1], d]
                        block = []

                        # Cleaning
                        break

                    cursor += 1

                if block:
                    pulled = new[map_.index(block_header[0])]
                    d: dict = pulled[2]
                    d.update({'code': block})
                    new[map_.index(block_header[0])] = [pulled[0], pulled[1], d]

                cursor -= 1

            cursor += 1

        cleared = []
        for line in new:
            if line[0] not in collected:
                cleared.append(list(line))
            else:
                cleared.append([line[0], 0, ''])

        another_cleared = []
        for line in cleared:
            if line[2]:
                another_cleared.append(line)

        return another_cleared

    # ------------------------------------------
    # Tools
    # ------------------------------------------

    @staticmethod
    def parse_math(line, num):
        """ Parses the mathematical thingy. As of fix 3.5.1, parse_math
        can now parse multiple numbers at once, which it could not do
        before because of it replacing the incorrect finds in the new
        line, not the original one. """

        keys = {
            '+': 'ADD',
            '-': 'SUB',
            '*': 'MUL',
            '/': 'DIV',
            '<': 'CSM',
            '>': 'CLG',
            '(': 'BRO',
            ')': 'BRC',
            '!=': 'NOT',
            '==': 'CEQ',
            '<=': 'CSE',
            '>=': 'CLE'
        }

        origin = line.replace(' ', '')
        line = line.replace(' ', '')
        finds = re.finditer('(!=|==|>=|<=|\+|-|\*|/|<|>|\(|\))', origin)
        for i in finds:
            x = origin[i.start():i.end()]
            try:
                line = line.replace(x, '¶' + keys[x] + '¶')
            except KeyError:
                raise SyntaxError(f'Invalid equation @ line {num}')

        temp = line.split('¶')
        # Clearing empty stuff
        line = []
        for i in temp:
            if i:
                line.append(i)
        for index, i in enumerate(line):
            try:
                line[index] = float(i)
            except ValueError:
                pass
        if len(line) <= 1:
            raise SyntaxError(f'Invalid equation @ line {num}')

        return line

    def parse_args(self, line, num):
        """ Parses the text and returns a data collected argument
        list. """

        # Omitting commas in lists
        levels = 0
        omits = []
        for i, c in enumerate(self.hash_strings(line, num)):
            if c == '[':
                levels += 1
            if c == ']':
                levels -= 1
            if levels >= 1 and c == ',':
                omits.append(i)

        splits = []
        for i, c in enumerate(self.hash_strings(line, num)):
            if c == ',' and not omits:
                splits.append(i)

        if splits:
            data = []
            cursor = 0
            for i in splits:
                data.append(self.variable(line[cursor:i], num))
                cursor = i + 1
            data.append(self.variable(line[cursor:], num))

            for i, s in enumerate(data):
                try:
                    data[i] = (s[0], s[1].replace(',', ' ').strip('"'))
                except AttributeError:
                    data[i] = s

        else:
            data = [self.variable(line, num)]

        return data

    def parse_array(self, line, num):
        """ Parses the array """

        elements = self.parse_args(line[1:-1], num)
        return 'array', elements

    def variable(self, data, num):
        """ Returns the proper version of the variable. The current
        types of variables this can return are: """
        # bool - booleans

        if data == 'True':
            return 'bool', True
        if data == 'False':
            return 'bool', False

        try:
            # num - Number
            data = float(data)
            data = ('num', data)
        except ValueError:

            if re.match(r'\[.*,.*\]', data):
                # Array
                elements = self.parse_args(data[1:-1], num)
                data = ('array', elements)
                return data

            if re.match(r'\w+\.\w+', data):
                call = data.split('.')[1]
                if re.match(r'\w+\.\w+\(.*\)', data):
                    # Function call
                    call = self.parse_call((num, 0, data.split('.', maxsplit=1)[1]))
                    call = call[2]
                return ('call', {
                    'module': data.split('.')[0],
                    'name': call['name'],
                    'params': call['params']
                })

            if '"' not in data:
                data = data.strip()
                if re.match(r'.*\[[0-9]+\]', data):
                    # elm - Element access
                    var = data.split('[')[0]
                    element = int(data.strip(']').strip().split('[')[1])
                    data = ('elm', {'var': var, 'element': element})

                else:
                    # Check for invalid chars in var name
                    data = data.strip()
                    if re.match('.*\W.*', data):
                        try:
                            data = self.parse_math(data, num)
                            return 'math', data
                        except SyntaxError:
                            raise SyntaxError(f'Invalid variable name @ line {num}')

                    # var - Variable
                    data = ('var', data)

            else:
                # Variable pre-check

                if re.match(r'[^#]', self.hash_strings(data.strip(), num)):
                    raise SyntaxError(f'Invalid variable format @ line {num}')

                # str - String
                escape_codes = {
                    '\\n': '\n',
                    '\\r': '\r',
                    '\\t': '\t',
                    '\\b': '\b',
                    '\\q': '"'
                }

                string = data.strip()[1:-1]
                for k, v in escape_codes.items():
                    string = string.replace(k, v)

                data = ('str', string)

        return data

    # ------------------------------------------
    # Statement types
    # ------------------------------------------

    def parse_if(self, line, kw='if'):
        """ Parses an if statement header. """
        index = line[0]
        indent = line[1]
        text = line[2]

        text = text.replace(kw, '')[:-1].strip()
        return [
            index, indent,
            {'type': kw, 'condition': self.parse_math(text, index)}
        ]

    def parse_elif(self, line):
        """ Parses an elif statement. """
        return self.parse_if(line, kw='elif')

    @staticmethod
    def parse_else(line):
        """ Just returns a structured else. """
        return [line[0], line[1], {'type': 'else'}]

    @staticmethod
    def parse_try(line):
        """ Just returns a structures else. """
        return [line[0], line[1], {'type': 'try'}]

    def parse_while(self, line):
        """ Parses an while statement. """
        return self.parse_if(line, kw='while')

    @apt.notimplemented
    def parse_for(self, line):
        """ This parses the for statement. This cannot be implemented
        yet because the lead dev has no idea how for loops should look. """

        return [
            line[0], line[1],
            {'type': 'for', ...: ...}
        ]

    def parse_call(self, line: tuple):
        """ Parses a function call. """
        index = line[0]
        indent = line[1]
        text = line[2]

        name = text.split('(', maxsplit=1)[0]
        params = self.parse_args(text.split('(', maxsplit=1)[1][:-1], index)

        return [
            index, indent,
            {'type': 'call', 'name': name, 'params': params}
        ]

    @staticmethod
    def parse_mixin(line: tuple):
        """ Parses a mixin statement """
        index = line[0]
        indent = line[1]
        text = line[2]

        return [
            index, indent,
            {'type': 'mixin', 'value': text.split(' ', maxsplit=1)[1]}
        ]

    @staticmethod
    def parse_header(line: tuple):
        """ Parses a function header. """
        index = line[0]
        indent = line[1]
        text = line[2]

        for c in ['#', ':', ')']:
            text = text.strip(c)
        name, params = text.split('(')
        a = re.finditer('[^A-z0-9_, ]', params)
        for find in a:
            if find:
                raise SyntaxError(f'Invalid function parameters @ line {index}')

        # Parameters
        params = [s.strip() for s in params.split(',')]

        return [
            index, indent,
            {'type': 'function', 'name': name, 'parameters': params}
        ]

    @staticmethod
    def parse_import(line: tuple):
        """ Parses an import statement. """
        try:
            import_ = line[2].split()[1]
        except IndexError:
            raise SyntaxError(f'Import statement cannot be empty @ line {line[0]}')
        return [
            line[0],
            line[1],
            {'type': 'import', 'name': import_}
        ]

    @staticmethod
    def parse_delete(line: tuple):
        """ Parses a delete statement """
        try:
            delete_ = line[2].split()[1]
        except IndexError:
            raise SyntaxError(f'Delete statement cannot be empty @ line {line[0]}')
        return [
            line[0],
            line[1],
            {'type': 'delete', 'var': delete_}
        ]

    def parse_statement(self, line: tuple):
        """ Parses a regular base statement. """
        index = line[0]
        indent = line[1]
        text = line[2]

        if len(text.split()) > 1:
            ins, params = text.split(maxsplit=1)
            # Parameter parsing
            params = self.parse_args(params, index)
        else:
            ins, params = text, []

        return [
            index, indent,
            {'type': 'statement', 'name': ins, 'params': params}
        ]

    def parse_assignment(self, line):
        """ Parses an assignment. """
        index = line[0]
        indent = line[1]
        text = line[2]

        var, data = (s.strip() for s in text.split('='))

        params = self.hash_strings(data, index)
        if '#' in params and '[' not in params and ']' not in params:
            for c in params:
                if c != '#':
                    raise SyntaxError(f'Invalid syntax @ line {index}')

        data = self.variable(data, index)

        return [
            index, indent,
            {'type': 'assignment', 'var': var, self.OPT_ASSIGNMENT_KW: data}
        ]

    # ------------------------------------------
    # Final
    # ------------------------------------------

    def render(self):
        """ Returns the code object from the class. Also places
        the header as the first element. """

        time_ = datetime.datetime.utcnow().strftime('%d-%M-%Y %H:%M:%S')
        header = {
            "line": 0,
            "type": self.OPT_HEADER_TITLE,
            "format": FORMAT,
            "info": f"Parsed by asp3 version {__version__}, {time_}"
        }
        self.code.insert(0, header)

        return self.code


def parse(lines: list, **kw):
    """ Parses the code and returns a JSON serializable data
    object which works as the code.
    :param lines: The lines of code, preferably coming from
    f.readlines() """

    return _Parser(lines, **kw).render()
