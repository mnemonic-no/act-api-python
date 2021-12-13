"""Common worker library"""

import argparse
import inspect
import os
import re
import sys
from logging import debug, error
from typing import Any, Callable, Dict, Optional, Text, cast

import caep

import act.api

CONFIG_ID = "act"
CONFIG_NAME = "act.ini"


def parseargs(description: str, fact_arguments=False) -> argparse.ArgumentParser:
    """Parse arguments"""
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description="{} ({})".format(description, worker_name()),
        epilog="""

  --config INI_FILE     Override default locations of ini file

    Arguments can be specified in ini-files, environment variables and
    as command line arguments, and will be parsed in that order.

    By default, configuration will be read from an ini file in /etc/{1}
    and ~/.config/{0}/{1} (or in $XDG_CONFIG_DIR if
    specified).

    Confiuration in "DEFAULT" section will be inherited by each secion.

    It is also possible to use environment variables for configuration.
    Environment variables should have the argument name in uppercase and
    "-" replaced with "_".

    E.g. set the CERT_FILE environment variable to configure the
    --cert-file option.

""".format(
            CONFIG_ID, CONFIG_NAME
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--http-timeout", type=int, default=120, help="Timeout")
    parser.add_argument("--proxy-string", help="Proxy to use for external queries")
    parser.add_argument(
        "--proxy-platform",
        action="store_true",
        help="Use proxy-string towards the ACT platform",
    )
    parser.add_argument(
        "--cert-file",
        help="Cerfiticate to add if you are behind a SSL/TLS interception proxy.",
    )
    parser.add_argument("--user-id", help="User ID")
    parser.add_argument("--act-baseurl", help="ACT API URI")
    parser.add_argument("--logfile", help="Log to file (default = stdout)")
    parser.add_argument("--loglevel", default="info", help="Loglevel (default = info)")
    parser.add_argument(
        "--http-header",
        help="Comma separated list of HTTP headers, e.g. "
        + "'HeaderA: val1, HeaderB:comma\\,val2",
    )

    parser.add_argument("--http-user", help="ACT HTTP Basic Auth user")
    parser.add_argument("--http-password", help="ACT HTTP Basic Auth password")

    if fact_arguments:
        parser.add_argument(
            "--output-format",
            dest="output_format",
            choices=["str", "json"],
            default="json",
            help="Output format for fact (default=json)",
        )
        parser.add_argument(
            "--access-mode",
            default=act.api.DEFAULT_ACCESS_MODE,
            choices=act.api.ACCESS_MODES,
            help="Specify default access mode used for all facts.",
        )
        parser.add_argument(
            "--organization", help="Specify default organization applied to all facts."
        )
        parser.add_argument(
            "--origin-name",
            dest="origin_name",
            help="Origin name. This name must be defined in the platform",
        )
        parser.add_argument(
            "--origin-id",
            dest="origin_id",
            help="Origin id. This must be the UUID of the origin in the platform",
        )
    return parser


def __mod_name(stack: inspect.FrameInfo) -> Text:
    """Return name of module from a stack ("_" is replaced by "-")"""
    mod = inspect.getmodule(stack[0])
    return os.path.basename(mod.__file__).replace(".py", "").replace("_", "-")


def worker_name() -> Text:
    """Return first external module that called this function, directly, or indirectly"""

    modules = [__mod_name(stack) for stack in inspect.stack() if __mod_name(stack)]
    return [name for name in modules if name != modules[0]][0]


def handle_args(parser: argparse.ArgumentParser) -> argparse.Namespace:
    """Wrapper for caep.handle_args where we set config_id and config_name"""
    args = caep.handle_args(parser, CONFIG_ID, CONFIG_NAME, worker_name())

    if args.http_header:
        # Convert comma separated list of http headers to dictionary
        headers = {}

        # Split on comma, unless they are escaped
        for header in re.split(r"(?<!\\),", args.http_header):
            if ":" not in header:
                raise act.api.base.ArgumentError(
                    f"No ':' in header, http header: {header}"
                )
            header_key, header_val = header.split(":", 1)
            header_key = header_key.strip().replace("\\,", ",")
            header_val = header_val.strip().replace("\\,", ",")
            headers[header_key] = header_val
        args.http_header = headers

    return cast(argparse.Namespace, args)


def fatal(message: Text, exit_code: int = 1) -> None:
    "Send error to error() and stderr() and exit with exit_code"
    sys.stderr.write(message.strip() + "\n")
    error(message.strip())
    sys.exit(exit_code)


def init_act(
    args: argparse.Namespace,
    object_formatter: Optional[Callable] = None,
    object_validator: Optional[Callable] = None,
) -> act.api.Act:
    """Initialize act api from arguments"""

    config = {
        "act_baseurl": args.act_baseurl,
        "user_id": args.user_id,
        "log_level": args.loglevel,
        "log_file": args.logfile,
        "log_prefix": worker_name(),
        # Provide defaults for optional arguments
        "origin_name": getattr(args, "origin_name", None),
        "origin_id": getattr(args, "origin_id", None),
        "access_mode": getattr(args, "access_mode", act.api.DEFAULT_ACCESS_MODE),
        "organization": getattr(args, "organization", None),
        "object_validator": object_validator,
        "object_formatter": object_formatter,
    }

    requests_kwargs: Dict[Text, Any] = {}

    if args.http_header:
        requests_kwargs["headers"] = args.http_header

    if args.http_user:
        requests_kwargs["auth"] = (args.http_user, args.http_password)

    if args.proxy_string and args.proxy_platform:
        requests_kwargs["proxies"] = {
            "http": args.proxy_string,
            "https": args.proxy_string,
        }

    if args.cert_file:
        requests_kwargs["verify"] = args.cert_file

    config["requests_common_kwargs"] = requests_kwargs

    api = act.api.Act(**config)

    if args.http_header:
        # Debug output of HTTP headers (must wait until act.api.Act() is initialized
        # so we have setup logging)
        debug("HTTP headers: %s", args.http_header)

    return api
