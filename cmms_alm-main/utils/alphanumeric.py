
from decimal import Decimal, InvalidOperation
import io
import json
import pprint
import re
from typing import Mapping, Iterable, Dict

# from deprecated import deprecated

NOT_PROVIDED = object()


def soft_parse(text, default=NOT_PROVIDED):
    err_str = f'{text} cannot be safely parsed'

    if isinstance(text, (bool, int, float, Decimal, type(None))):
        return text
    if not isinstance(text, str):
        raise TypeError(err_str)

    if text.isdigit():
        return int(text)

    try:
        return float(text)
    except:
        pass

    text = text.lower()
    if text in ['null', 'none']:
        return None

    if text in ['ok', 'on']:
        return True

    if text in ['off']:
        return False

    if text.startswith(('y', 't')):
        return True
    if text.startswith(('n', 'f')):
        return False

    # Default
    if default != NOT_PROVIDED:
        return default

    raise ValueError(err_str)


def getitem_parse(d: Dict, key, default=NOT_PROVIDED):

    if default == NOT_PROVIDED:
        val = d[key]
    else:
        val = d.get(key, default)

    return soft_parse(val, default)

# @deprecated
def str2bool(text, default=NOT_PROVIDED):
    return bool(soft_parse(text, default))


def isNull(text):
    """
    Test if a string 'looks' like a null value.
    This is useful for querying the API against a null key.

    Args:
        text: Input text

    Returns:
        True if the text looks like a null value
    """

    return str(text).strip().lower() in ['top', 'null', 'none', 'empty', 'false', '-1', '']


def split_prefix_number(string):
    pattern = r"(.*?)(\d+)?$"

    result = re.search(pattern, string)

    # No match!
    if result is None:
        return string

    groups = result.groups()

    # If we cannot match the regex, then simply return the provided value
    if not len(groups) == 2:
        return string

    prefix, number = groups
    return prefix, number


def increment(n, force=False):
    """Attempt to increment an integer (or a string that looks like an integer!)

    Examples
    --------
    For examples, see `Kaizntree/tests.py > TestIncrement`

    Parameters
    ----------
    n : str
        [description]
    force : bool, optional
        If , by default False

    Returns
    -------
    str
        [description]
    """

    value = str(n).strip()

    # Ignore empty strings
    if not value:
        return value

    prefix, number = split_prefix_number(value)

    # No number extracted? Simply return the prefix (without incrementing!)
    if not number:
        if force:
            return prefix + '1'
        else:
            return prefix

    # Record the width of the number
    width = len(number)

    try:
        number = int(number) + 1
        number = str(number)
    except ValueError:
        pass

    number = number.zfill(width)

    return prefix + number


def next_available(
    used_names:Iterable[str], initial:str=None,
    force=False, return_initial=False,
):
    """Finds the next available "name". It starts with `initial`, and avoids
    names already in `used_names`. To find the "next" iteration, it uses
    `increment`.

    Example
    -------
    ```python
    next_available(['hello2', 'hello3'], 'hello1') == 'hello4'
    ```

    Parameters
    ----------
    used_names : Iterable[str]
        Already-used names. Will never return one of these
    initial : str
        Initial name to try. Defaults to the first item in `used_names`
    force : bool
        Defaults to True.
    return_initial : bool
        Whether it is possible to return `initial` if it is not in `used_names`
        By default False.
    """
    # Initial cleaning
    name_iter = iter(used_names)
    name_set = set(used_names)
    if initial is None:
        if return_initial :
            raise ValueError(
                'Cannot use `return_initial` if `initial` is not provided.'
            )
        try:
            initial = next(name_iter)
        except StopIteration:
            raise ValueError(
                '`used_names` cannot be empty if `initial` is not provided.'
            )

    #
    if initial not in name_set and return_initial:
        return initial

    tries = set([initial])
    name = initial

    while 1:
        name = increment(name, force)

        if name in tries:
            # We are in a looping situation
            if force:
                name += '1'
            else:
                return name

        # Check that the new ref does not exist in the database
        if name in name_set:
            tries.add(name)

        else:
            break

    return name


def normalize(d, _round=True):
    """
    Normalize a decimal number, and remove exponential formatting.

    Reference
    ----------
    https://docs.python.org/3/library/decimal.html
    """

    d = Decimal(d)
    # Truncate huge decimals
    d = d.quantize(Decimal('1.00000')) if _round else d
    d = d.normalize()

    if d == d.to_integral():
        d = d.quantize(Decimal('1'))

    return d


def decimal2string(d):
    """
    Format a Decimal number as a string,
    stripping out any trailing zeroes or decimal points.
    Essentially make it look like a whole number if it is one.

    Args:
        d: A python Decimal object

    Returns:
        A string representation of the input number
    """

    try:
        # Ensure that the provided string can actually be converted to a decimal
        d = normalize(d, True)
    except (ValueError, InvalidOperation):
        # Not a number
        return str(d)

    s = str(d)

    # Return entire number if there is no decimal place
    if '.' not in s or d % 10 == 0:
        return s

    return s.rstrip("0").rstrip(".")


APPROX_MAX = 1.001
APPROX_MIN = 0.999


def approxBigger(val1, val2):
    """ val1 >~ val2 """
    return float(val1) > float(val2) * APPROX_MAX


def approxSmaller(val1, val2):
    """ val1 ~< val2 """
    return float(val1) < float(val2) * APPROX_MIN


def approxEq(val1, val2):
    """ val1 ~= val2s """
    return (not approxBigger(val1, val2)) and (not approxSmaller(val1, val2))


def wrap_with_quotes(text, quote='"'):
    """ Wrap the supplied text with quotes

    Args:
        text: Input text to wrap
        quote: Quote character to use for wrapping (default = "")

    Returns:
        Supplied text wrapped in quote char
    """

    if not text.startswith(quote):
        text = quote + text

    if not text.endswith(quote):
        text = text + quote

    return text


def pprint_str(obj, **kwargs):
    """ Returns the string of pprint.pprint """
    stream = io.StringIO()
    pprint.pprint(obj, stream, **kwargs)
    stream.seek(0)
    return stream.read()


def clean_html(html_string: str):
    """ will extract the body of the HTML and remove the `script` tags.

    Example
    -------
    Will turn this
    ```html
    <!DOCTYPE html>
    <html>
    <head>
        <title>Some Document</title>
    </head>
    <body>
        <p>The body</p>
        <div>
            <p>A box</p>
        </div>
        <script>console.log("Maybe I'm malicious")</script>
    </body>
    </html>
    ```
    into
    ```html
    <p>The body</p>
    <div>
        <p>A box</p>
    </div>
    ```

    Parameters
    ----------
    html_string : str
        A valid HTML string.

    Returns
    -------
    str
        the cleaned HTML
    """
    space = r'(?:\s|\n)*'
    before_head = rf'^{space}<!DOCTYPE html>{space}<html.*?>{space}<head.*?>.*?<\/head>{space}<body.*?>{space}'
    after_body = rf'<\/body>{space}<\/html>{space}$'

    flags = re.IGNORECASE | re.DOTALL
    html_string = re.sub(before_head, '', html_string, count=1, flags=flags)
    html_string = re.sub(after_body, '', html_string, count=1, flags=flags)
    html_string = re.sub(r'<script.*?>.*?</script>', '', html_string, flags=flags)

    return html_string


# regex from https://www.emailregex.com/
extract_email_regex = re.compile(
    r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"
)


def jsonify(obj):
    """ Transforms an object into a JSON-compatible representation """
    return json.loads(json.dumps(obj))
