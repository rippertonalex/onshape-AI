from typing import Tuple


def get_arg(args: dict, arg_name: str, type: any, default=None) -> Tuple:
    """Get argument from request args.

    Args:
        args (dict): The request args.
        arg_name (str): The argument name.
        default (any, optional): The default value. Defaults to None.

    Returns:
        Tuple: The argument value.
    """
    arg = args.get(arg_name, default) if args else default

    if arg is not None:
        arg = type(arg)

    return arg


def get_pagination_args(args: dict) -> Tuple:
    """Get pagination arguments from request args.

    Args:
        args (dict): The request args.

    Returns:
        Tuple: The pagination arguments.
    """
    page = get_arg(args, "page", int, 1)
    per_page = get_arg(args, "per_page", int, 10)

    return page, per_page
