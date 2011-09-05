#! /usr/bin/env python
# -*- conding: utf-8 -*-

import argparse
import sys
import os
import fnmatch
import string
import re

default_license_dir = os.path.expanduser("~/.codelicensator")

def checkVarAssignments(var_assignments):
    if not re.match("^(|([A-Z_]+=[^,]+,)*([A-Z_]+=[^,]+))$", var_assignments):
        print("bad var assignments format")
        sys.exit(1)

def wildcardsToRegex(wildcard):
    regex = wildcard

    squares = re.findall(r"\[([^\[\]]+)\]", regex)
    regex = re.sub(r"\[[^\[\]]+\]", "[]", regex)

    curlies = re.findall("\{([^\{\}]+)\}", regex)
    regex = re.sub("\{([^\{\}]+)+[^\{\}]+\}", "{}", regex)

    regex = re.escape(regex)

    regex = re.sub(r"\\\*", ".*", regex)
    regex = re.sub(r"\\\?", ".", regex)

    for square in squares:
        square = re.escape(square)
        square = re.sub(r"^\\!", "^", square)
        square = re.sub(r"\\\-", "-", square)
        regex = re.sub(r"\\\[\\\]", "[" + square + "]", regex, 1)

    for curly in curlies:
        curly = re.escape(curly)
        curly = re.sub(r"\\\,", "|", curly)
        regex = re.sub(r"\\\{\\\}", "(" + curly + ")", regex, 1)

    return "^" + regex + "$"

def extract_vars(licensetext):
    vars = re.findall("%([A-Z_]+)%", licensetext)
    vars = list(set(vars))
    return vars

def make_dict(var_assignments):
    dict = {}

    if var_assignments:
        for assignment in var_assignments.split(","):
            var = assignment.split("=")
            dict[var[0]] = var[1]

    return dict

def assing_vars(licensetext, var_assignments):
    checkVarAssignments(var_assignments)
    varlist = extract_vars(licensetext)
    vardict = make_dict(var_assignments)

    for var in varlist:
        if var in vardict:
            licensetext = re.sub("%" + var + "%", vardict[var], licensetext)
        else:
            print("Error: variable " + var + " hasn't assigned any value")
            sys.exit(1)

    return licensetext

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Add license to the files")
    parser.add_argument("workingdir", metavar="working-dir", help="directory where to seek recursively for files")
    parser.add_argument("license", help="name of the license file without extension")
    parser.add_argument("filter", metavar="file-filter", help="wildcard of files to be licensed", default="*", nargs="?")
    parser.add_argument(
            "-l", "--license-dir", metavar="DIR",
            help="direcotry with licenses (default is " + default_license_dir + ")",
            required=False, default=default_license_dir
    )
    parser.add_argument("-r", "--replace", help="replace license in source file if another exists", action="store_true")
    parser.add_argument(
            "-v", "--vars", help="list of license variable assignments (example: YEAR=2011,AUTHOR=John Blake)",
            default=""
    )
    args = parser.parse_args()

    if not os.path.isdir(args.workingdir):
        print(args.workingdir + " is not directory")
        sys.exit(1)

    license_dir = os.path.expanduser(args.license_dir)

    if license_dir == default_license_dir:
        if not os.path.exists(license_dir):
            os.mkdir(license_dir)
            print("creating default '" + license_dir + "' directory")

    try:
        licenses = os.listdir(license_dir)
    except OSError as e:
        print(e)
        sys.exit(1)

    if not args.license in licenses:
        print("Error: there is no license '" + args.license + "'")
        print("Available licenses:", " ".join(licenses));
        sys.exit(1)
    
    licensefile = open(os.path.join(license_dir, args.license), "r")
    licensetext = licensefile.read();

    licensetext = assing_vars(licensetext, args.vars)

    filter = wildcardsToRegex(args.filter);

    for dir, _, files in os.walk(args.workingdir):
        for file in files:
            filepath = os.path.join(dir, file)

            if re.match(filter, filepath):
                file = open(filepath, "r")
                filecontent = file.read()
                file.close()

                match = re.match("^(.*)(\/\*((?!\*/).)*copyright((?!\*/).)*\*\/)\\n(.*)$", filecontent, re.DOTALL | re.IGNORECASE)
                if match:
                    if args.replace:
                        print("replacing license:", filepath)
                        file = open(filepath, "w")
                        file.write(match.group(1) + licensetext + match.group(5))
                    else:
                        print("already licensed:", filepath)
                else:
                    print("adding license:", filepath)
                    file = open(filepath, "w")
                    file.write(licensetext + "\n" + filecontent)
