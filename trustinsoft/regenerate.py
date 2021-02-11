#! /usr/bin/env python3

# This script regenerates TrustInSoft CI configuration.

# Run from the root of the project:
# $ python3 trustinsoft/regenerate.py

import tis

import re # sub
import json # dumps, load
import os # makedirs
from os import path # path.basename, path.isdir, path.join
import glob # iglob
from itertools import product  # Cartesian product of lists.
import shutil # copyfileobj
import argparse # ArgumentParser, add_argument, parse_args

# --------------------------------------------------------------------------- #
# ----------------------------- PARSE ARGUMENTS ----------------------------- #
# --------------------------------------------------------------------------- #

parser = argparse.ArgumentParser(
    description="Regenerate the TrustInSoft CI files.",
    epilog="Please call this script only after building RHash.")
args = parser.parse_args()

# --------------------------------------------------------------------------- #
# -------------------------------- SETTINGS --------------------------------- #
# --------------------------------------------------------------------------- #

# Directories.
common_config_path = path.join("trustinsoft", "common.config")

# Architectures.
machdeps = [
    {
        "machdep": "gcc_x86_32",
        "pretty_name": "little endian 32-bit (x86)",
        "fields": {
            "address-alignment": 32,
        }
    },
    {
        "machdep": "gcc_x86_64",
        "pretty_name": "little endian 64-bit (x86)",
        "fields": {
            "address-alignment": 64
        }
    },
    {
        "machdep": "gcc_ppc_32",
        "pretty_name": "big endian 32-bit (PPC32)",
        "fields": {
            "address-alignment": 32,
        },
    },
    {
        "machdep": "gcc_ppc_64",
        "pretty_name": "big endian 64-bit (PPC64)",
        "fields": {
            "address-alignment": 64,
        },
    },
]

# --------------------------------------------------------------------------- #
# ---------------------------------- CHECKS --------------------------------- #
# --------------------------------------------------------------------------- #

# Initial check.
print("1. Check if all necessary directories and files exist...")
tis.check_dir("trustinsoft")

# --------------------------------------------------------------------------- #
# -------------------- GENERATE trustinsoft/common.config ------------------- #
# --------------------------------------------------------------------------- #

def make_common_config():
    files = list(filter(
        lambda file:
            file != "rhash_main.c" and
            file != path.join("librhash", "test_hashes.c") and
            file[0] != '_',
        sorted(glob.glob("*.c")) +
        sorted(glob.glob(path.join("librhash", "*.c")))
    ))
    return {
        "prefix_path": "..",
        "files": [ "trustinsoft/stub.c" ] + files,
        "cpp-extra-args": [
            "-Dvolatile=",
            "-I.",
            "-Ilibrhash",
            "-DNDEBUG",
            "-UUSE_OPENSSL",
            "-DRHASH_XVERSION=0x01040000",
            "-DLOCALEDIR=\"/usr/local/share/locale\""
        ],    
        "val-warn-harmless-function-pointers": False,
    }

common_config = make_common_config()
with open(common_config_path, "w") as file:
    print("3. Generate the '%s' file." % common_config_path)
    file.write(tis.string_of_json(common_config))

# ---------------------------------------------------------------------------- #
# ------------------ GENERATE trustinsoft/<machdep>.config ------------------- #
# ---------------------------------------------------------------------------- #

def make_machdep_config(machdep):
    machdep_config = {
        "machdep": machdep["machdep"]
    }
    fields = machdep["fields"]
    for field in fields:
        machdep_config[field] = fields[field]
    return machdep_config

print("4. Generate 'trustinsoft/<machdep>.config' files...")
machdep_configs = map(make_machdep_config, machdeps)
for machdep_config in machdep_configs:
    file = path.join("trustinsoft", "%s.config" % machdep_config["machdep"])
    with open(file, "w") as f:
        print("   > Generate the '%s' file." % file)
        f.write(tis.string_of_json(machdep_config))

# --------------------------------------------------------------------------- #
# --------------------------- GENERATE tis.config --------------------------- #
# --------------------------------------------------------------------------- #

rhash_main_tests = [
    {
        "name": "test with a text string",
        "val-args": "~--message~\"abc\"",
    },
    {
        "name": "test stdin processing",
        "filesystem": {
            "files": [
                {
                    "from": "trustinsoft/inputs/abc_stdin",
                    "name": "tis-mkfs-stdin",
                }
            ]
        },
        "val-args": "~-CHMETAGW~--sfv~-",
    },
    {
        "name": "test with 1Kb data file",
        "filesystem": {
            "files": [
                {
                    "from": "tests/test1K.data",
                    "name": "test1K.data",
                }
            ]
        },
        "val-args": "~--printf~\"%f %C %M %H %E %G %T %A %W\\n\"~test1K.data",
    },
    {
        "name": "test calculation/verification of reversed GOST hashes with 1Kb data file",
        "filesystem": {
            "files": [
                {
                    "from": "tests/test1K.data",
                    "name": "test1K.data",
                }
            ]
        },
        "val-args": "~--simple~--gost~--gost-cryptopro~--gost-reverse~test1K.data",
    },
    {
        "name": "test calculation/verification of reversed GOST hashes with 1Kb data file (rev)",
        "filesystem": {
            "files": [
                {
                    "from": "trustinsoft/inputs/test1K.data_GOST_result",
                    "name": "tis-mkfs-stdin",
                }
            ]
        },
        "val-args": "~-vc~-",
    },
    {
        "name": "test handling empty files",
        "filesystem": {
            "files": [
                {
                    "max_val": 0,
                    "min_val": 0,
                    "name": "test-empty.file",
                    "size": 0,
                }
            ]
        },
        "val-args": "~-p~\"%m\"~test-empty.file",
    },
    {
        "name": "test processing of empty message",
        "val-args": "~-p~\"%m\"~-m~\"\"",
    },
    {
        "name": "test processing of empty stdin",
        "filesystem": {
            "files": [
                {
                    "max_val": 0,
                    "min_val": 0,
                    "name": "tis-mkfs-stdin",
                    "size": 0,
                }
            ]
        },
        "val-args": "~-p~\"%m\"~-",
    },
    {
        "name": "test verification of empty file",
        "filesystem": {
            "files": [
                {
                    "max_val": 0,
                    "min_val": 0,
                    "name": "test-empty.file",
                    "size": 0,
                }
            ]
        },
        "val-args": "~-c~\"test-empty.file\"",
    },
    {
        "name": "test %x, %b, %B modifiers",
        "val-args": "~-p~'%f %s %xC %bc %bM %Bh %bE %bg %xT %xa %bW\\n'~-m~\"a\"",
    },
]

def make_rhash_main_test(rhash_main_test, machdep):
    test = dict()
    test["name"] = rhash_main_test["name"]
    test["files"] = [ "rhash_main.c" ]
    test["include"] = common_config_path
    test["include_"] = path.join("trustinsoft", "%s.config" % machdep["machdep"])
    if "filesystem" in rhash_main_test:
        test["filesystem"] = rhash_main_test["filesystem"]
    if "val-args" in rhash_main_test:
        test["val-args"] = rhash_main_test["val-args"]
    return test

librhash_tests = [
    "test_all_known_strings",
    "test_long_strings",
    "test_results_consistency",
    "test_unaligned_messages_consistency",
    "test_magnet",
    "main",
]

def make_librhash_test(librhash_test, machdep):
    test_hashes_C_path = path.join("librhash", "test_hashes.c")
    return {
        "name": "%s : %s" % (test_hashes_C_path, librhash_test),
        "main": librhash_test,
        "files": [ test_hashes_C_path ],
        "include": common_config_path,
        "include_": path.join("trustinsoft", "%s.config" % machdep["machdep"])
    }

tis_test_long_strings_cases = list(range(0, 32))

def make_tis_test_long_strings(case_no, machdep):
    test = make_librhash_test("test_long_strings", machdep)
    test["name"] += (" : %d" % case_no)
    test["main"] = "tis_test_long_strings"
    test["cpp-extra-args"] = [ "-DTEST_CASE=%d" % case_no ]
    return test

def make_tis_config():
    return (
        list(map(
            lambda t: make_rhash_main_test(t[0], t[1]),
            product(rhash_main_tests, machdeps)
        )) +
        list(map(
            lambda t: make_librhash_test(t[0], t[1]),
            product(librhash_tests, machdeps)
        )) + 
        list(map(
            lambda t: make_tis_test_long_strings(t[0], t[1]),
            product(tis_test_long_strings_cases, machdeps)
        ))
    )

tis_config = make_tis_config()
with open("tis.config", "w") as file:
    print("5. Generate the 'tis.config' file.")
    file.write(tis.string_of_json(tis_config))
