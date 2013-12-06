#!/usr/bin/python

import argparse
import sys

from string import Template

parser = argparse.ArgumentParser(
    description='replace Cloud Formation Template variables')

parser.add_argument('-t', '--template', default="aws/cloudformation.template",
                    help="Cloud Formation Template to process")
parser.add_argument('-g', '--group', action='append', default=[],
                    help="Instance Security Groups\nRepeat for each group")
parser.add_argument('-k', '--keypair', default="default",
                    help="Instance Key Pair")
parser.add_argument('-r', '--role', default="autoroute",
                    help="Instance Role")
parser.add_argument('-o', '--options', default='',
                    help="arguments for the autoroute upstart job")
parser.add_argument(
    '-a', '--ami', action='append', default=[],
    help="region and ami as a tuple, ex: us-west-1,ami-c08dbc85\n"
         "can be repeated for each region")

args = parser.parse_args()
opts = vars(args)

for combo in args.ami:
    try:
        (region, ami) = combo.split(',')
        opts['ami_%s' % region.strip().replace('-', '_')] = ami.strip()
    except Exception as e:
        sys.stderr.write("invalid ami tuple '%s': %s\n" % (combo, str(e)))

# strip whitespace and join groups
opts['groups'] = ",".join([g.strip() for g in args.group])

with open(args.template) as f:
    content = f.read()
    template = Template(content)

    print template.safe_substitute(opts)
