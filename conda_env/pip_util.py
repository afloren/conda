# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.env.pip_util` instead.

Environment object describing the conda environment.yaml file.
"""
import json
import os
import re
import sys

from conda.deprecations import deprecated

# Import from conda.env.pip_util since this module is deprecated.
from conda.env.pip_util import (  # noqa
    get_pip_installed_packages,
    pip_subprocess,
)
from conda.exceptions import CondaEnvException

deprecated.module("24.9", "25.3", addendum="Use `conda.env.pip_util` instead.")


@deprecated("23.9", "24.3")
def get_pip_version(prefix):
    stdout, stderr = pip_subprocess(["-V"], prefix)
    pip_version = re.search(r"pip\ (\d+\.\d+\.\d+)", stdout)
    if not pip_version:
        raise CondaEnvException("Failed to find pip version string in output")
    else:
        pip_version = pip_version.group(1)
    return pip_version


@deprecated("23.9", "24.3")
class PipPackage(dict):
    def __str__(self):
        if "path" in self:
            return "{} ({})-{}-<pip>".format(
                self["name"], self["path"], self["version"]
            )
        return "{}-{}-<pip>".format(self["name"], self["version"])


@deprecated("23.9", "24.3")
def installed(prefix, output=True):
    pip_version = get_pip_version(prefix)
    pip_major_version = int(pip_version.split(".", 1)[0])

    env = os.environ.copy()
    args = ["list"]

    if pip_major_version >= 9:
        args += ["--format", "json"]
    else:
        env["PIP_FORMAT"] = "legacy"

    try:
        pip_stdout, stderr = pip_subprocess(args, prefix=prefix, env=env)
    except Exception:
        # Any error should just be ignored
        if output:
            print("# Warning: subprocess call to pip failed", file=sys.stderr)
        return

    if pip_major_version >= 9:
        pkgs = json.loads(pip_stdout)

        # For every package in pipinst that is not already represented
        # in installed append a fake name to installed with 'pip'
        # as the build string
        for kwargs in pkgs:
            kwargs["name"] = kwargs["name"].lower()
            if ", " in kwargs["version"]:
                # Packages installed with setup.py develop will include a path in
                # the version. They should be included here, even if they are
                # installed with conda, as they are preferred over the conda
                # version. We still include the conda version, though, because it
                # is still installed.

                version, path = kwargs["version"].split(", ", 1)
                # We do this because the code below uses rsplit('-', 2)
                version = version.replace("-", " ")
                kwargs["version"] = version
                kwargs["path"] = path
            yield PipPackage(**kwargs)
    else:
        # For every package in pipinst that is not already represented
        # in installed append a fake name to installed with 'pip'
        # as the build string
        pat = re.compile(r"([\w.-]+)\s+\((.+)\)")
        for line in pip_stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            m = pat.match(line)
            if m is None:
                if output:
                    print(
                        "Could not extract name and version from: %r" % line,
                        file=sys.stderr,
                    )
                continue
            name, version = m.groups()
            name = name.lower()
            kwargs = {
                "name": name,
                "version": version,
            }
            if ", " in version:
                # Packages installed with setup.py develop will include a path in
                # the version. They should be included here, even if they are
                # installed with conda, as they are preferred over the conda
                # version. We still include the conda version, though, because it
                # is still installed.

                version, path = version.split(", ")
                # We do this because the code below uses rsplit('-', 2)
                version = version.replace("-", " ")
                kwargs.update(
                    {
                        "path": path,
                        "version": version,
                    }
                )
            yield PipPackage(**kwargs)


# canonicalize_{regex,name} inherited from packaging/utils.py
# Used under BSD license
_canonicalize_regex = re.compile(r"[-_.]+")


@deprecated("23.9", "24.3")
def _canonicalize_name(name):
    # This is taken from PEP 503.
    return _canonicalize_regex.sub("-", name).lower()


@deprecated("23.9", "24.3")
def add_pip_installed(prefix, installed_pkgs, json=None, output=True):
    # Defer to json for backwards compatibility
    if isinstance(json, bool):
        output = not json

    # TODO Refactor so installed is a real list of objects/dicts
    #      instead of strings allowing for direct comparison
    # split :: to get rid of channel info

    # canonicalize names for pip comparison
    # because pip normalizes `foo_bar` to `foo-bar`
    conda_names = {_canonicalize_name(rec.name) for rec in installed_pkgs}
    for pip_pkg in installed(prefix, output=output):
        pip_name = _canonicalize_name(pip_pkg["name"])
        if pip_name in conda_names and "path" not in pip_pkg:
            continue
        installed_pkgs.add(str(pip_pkg))
