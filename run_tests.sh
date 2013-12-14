#!/bin/bash

function usage {
  echo "Usage: $0 [OPTION]..."
  echo "Run Callme's test suite(s)"
  echo ""
  echo "  -p, --pep8               Run pep8"
  echo "  -l, --pylint             Run pylint"
  echo "  -c, --cover              Run unit tests with coverage"
  echo "  -i, --integration        Run integration tests"
  echo "  -f, --force              Force re-create virtual environments"
  echo ""
  echo "  -h, --help               Print this usage message"
  echo ""
  echo "Note: with no options specified, the script will run unit tests with default tox environments."
  exit
}

function process_option {
  case "$1" in
    -h|--help) usage;;
    -p|--pep8) toxopts="$toxopts -epep8";;
    -l|--pylint) toxopts="$toxopts -epylint";;
    -c|--cover) toxopts="$toxopts -ecover";;
    -i|--integration) toxopts="$toxopts -eintegration";;
    -f|--force) toxopts="$toxopts -r";;
    -*) toxopts="$toxopts $1";;
    *) toxargs="$toxargs $1"
  esac
}

toxopts=
toxargs=

for arg in "$@"; do
  process_option $arg
done

function run_tests {
  tox $toxopts $toxargs
}

run_tests || exit
