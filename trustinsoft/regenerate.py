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

not_64 = [
    "-U_LP64",
    "-U__LP64__",
    "-U__x86_64",
    "-U__x86_64__",
    "-U_M_AMD64",
    "-U_M_X64",
]

# No matter the architecture, the dynamically allocated addresses are always
# aligned according to the DEFAULT_ALIGNMENT macro, which is a constant always
# set to 64.
DEFAULT_ALIGNMENT = 64

# Architectures.
machdeps = [
    {
        "machdep": "gcc_x86_32",
        "pretty_name": "little endian 32-bit (x86)",
        "fields": {
            "address-alignment": DEFAULT_ALIGNMENT,
            "cpp-extra-args": not_64
        }
    },
    {
        "machdep": "gcc_x86_64",
        "pretty_name": "little endian 64-bit (x86)",
        "fields": {
            "address-alignment": DEFAULT_ALIGNMENT
        }
    },
    {
        "machdep": "gcc_ppc_32",
        "pretty_name": "big endian 32-bit (PPC32)",
        "fields": {
            "address-alignment": DEFAULT_ALIGNMENT,
            "cpp-extra-args": not_64
        },
    },
    {
        "machdep": "gcc_ppc_64",
        "pretty_name": "big endian 64-bit (PPC64)",
        "fields": {
            "address-alignment": DEFAULT_ALIGNMENT,
            "cpp-extra-args": not_64
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
            "-DLOCALEDIR=\"/usr/local/share/locale\"",
            "-DRHASH_NO_ASM",
            "-DRHASH_XVERSION=0x01040000",
            "-UUSE_OPENSSL",
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
    test["name"] = "%s, %s" % (rhash_main_test["name"], machdep["pretty_name"])
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
    # "test_long_strings", # This is too long, divided into separate cases.
    "test_results_consistency",
    "test_unaligned_messages_consistency",
    "test_magnet",
    # "main", # This is too long and redundant with the previous ones.
]

def make_librhash_test(librhash_test, machdep):
    test_hashes_C_path = path.join("librhash", "test_hashes.c")
    return {
        "name": "%s : %s, %s" % (test_hashes_C_path, librhash_test, machdep["pretty_name"]),
        "main": librhash_test,
        "files": [ test_hashes_C_path ],
        "include": common_config_path,
        "include_": path.join("trustinsoft", "%s.config" % machdep["machdep"])
    }

long_strings_tests = [
    { 
        "hash_id": "CRC32",
        "expected_hash": "467ED497"
    },
    { 
        "hash_id": "CRC32C",
        "expected_hash": "3128C6CB"
    },
    { 
        "hash_id": "MD4",
        "expected_hash": "9C88157A6F588E9815A9E6B60877D93E"
    },
    { 
        "hash_id": "MD5",
        "expected_hash": "0D0C9C4DB6953FEE9E03F528CAFD7D3E"
    },
    { 
        "hash_id": "SHA1",
        "expected_hash": "A080CBDA64850ABB7B7F67EE875BA068074FF6FE"
    },
    { 
        "hash_id": "ED2K",
        "expected_hash": "9C88157A6F588E9815A9E6B60877D93E"
    },
    { 
        "hash_id": "AICH",
        "expected_hash": "UCAMXWTEQUFLW637M7XIOW5ANADU75X6"
    },
    { 
        "hash_id": "TIGER",
        "expected_hash": "64EE4377C6BBE3A4C1963B6377CD68095F323F0E8E31ED22"
    },
    { 
        "hash_id": "TTH",
        "expected_hash": "BGOMMS6M6WVMYKELCO5BDMY4SS4SVCOA5X6DWGI"
    },
    { 
        "hash_id": "WHIRLPOOL",
        "expected_hash": "46639D6913ABF0FDBF31811EB66D5B86E1D369DD66C9A6DA81BE9B553A647A2F117EDB97FC237A23067043C7F68C2D8CC71B210862C1C716846AD11CD3FCBD98"
    },
    { 
        "hash_id": "RIPEMD160",
        "expected_hash": "EB33E86B2400CC0A11707BE717A35A9ACF074A58"
    },
    { 
        "hash_id": "GOST94_CRYPTOPRO",
        "expected_hash": "990DDD66E568294EE27A0C1E75BEF8E129C82832F7BABFDB3DB9D5210FA63752"
    },
    { 
        "hash_id": "GOST94",
        "expected_hash": "157782019557056EC7F756C26C5B6064048194C2E3FAB6A898DC4C3B882D0370"
    },
    { 
        "hash_id": "HAS160",
        "expected_hash": "17DB25293425CEA5FC78539654264B06A9FB2FB4"
    },
    { 
        "hash_id": "SNEFRU128",
        "expected_hash": "6256051A29F8D69D662169585670BB9A"
    },
    { 
        "hash_id": "SNEFRU256",
        "expected_hash": "407FE84009C371702FE9C4C0436AA271A62B702E96111F5747DC03EA18FBDBA6"
    },
    { 
        "hash_id": "SHA224",
        "expected_hash": "00568FBA93E8718C2F7DCD82FA94501D59BB1BBCBA2C7DC2BA5882DB"
    },
    { 
        "hash_id": "SHA256",
        "expected_hash": "27DD1F61B867B6A0F6E9D8A41C43231DE52107E53AE424DE8F847B821DB4B711"
    },
    { 
        "hash_id": "SHA384",
        "expected_hash": "2BCA3B131BB7E922BCD1DE98C44786D32E6B6B2993E69C4987EDF9DD49711EB501F0E98AD248D839F6BF9E116E25A97C"
    },
    { 
        "hash_id": "SHA512",
        "expected_hash": "0593036F4F479D2EB8078CA26B1D59321A86BDFCB04CB40043694F1EB0301B8ACD20B936DB3C916EBCC1B609400FFCF3FA8D569D7E39293855668645094BAF0E"
    },
    { 
        "hash_id": "SHA3_224",
        "expected_hash": "DEC1633E9A1F4BB6B2DBE04C38E4B43BA4C865165031E6A11E3EA389"
    },
    { 
        "hash_id": "SHA3_256",
        "expected_hash": "B61166B03A22F4ACE84E2AD281780AABBF3EB436CC71D281CEF9D8CAE1E1236D"
    },
    { 
        "hash_id": "SHA3_384",
        "expected_hash": "3323B42EF9C5B7321C47A27DD9C322F2AEF86EEEECB80D0344E51B29FCC5098D3C406CA94075BFD0DB8D062058724507"
    },
    { 
        "hash_id": "SHA3_512",
        "expected_hash": "E1F5A8A3D74990804F4E01FDB67D99E578C624D45C3DC2AA4EB1B9932644AF685E711708751FCC4E19FE9FA790572E2C328309AC3C17E97DEDF5AFCEBCFE118E"
    },
    { 
        "hash_id": "EDONR256",
        "expected_hash": "7CEFFD4222364F22AC6894386E039776E809B663990AB5098DC8086FCE8C4775"
    },
    { 
        "hash_id": "EDONR512",
        "expected_hash": "38D648FCB9F9146B235A68090B4A5A1250457B9B1296CA879FC41FC9621872F42AF951ADDA34895379CF9183E2141D0BABB70BFB2F1A44F332800F9E506B6A9C"
    },
    { 
        "hash_id": "GOST12_256",
        "expected_hash": "96054632C841E681072F3585F5535A3DB8C4AB73097FD1373B79943EC7244E18"
    },
    { 
        "hash_id": "GOST12_512",
        "expected_hash": "A3AD7AB0F63BCA7D38E5C34718836A0AEE3137DFCE6038F318B6B3C212537C84CE5F8940424C4BCC10A46F3C12D1CFCE6402E3879FDBE03FDFC4A711E8894634"
    },
    { 
        "hash_id": "BTIH",
        "expected_hash": "D6C874BC44C9283DCD2EA64EC1F9BFC7B530EE20",
        "set_filename": True
    },
    {
        "hash_id": "BTIH",
        "expected_hash": "B99731F317F9FB4B5FA24D616B1EF5B59A063C1C"
    },
    {
        "hash_id": "GOST94",
        "ch": "0xFF",
        "msg_size": 64,
        "expected_hash": "13416C4EC74A63C3EC90CB1748FD462C7572C6C6B41844E48CC1184D1E916098"
    },
    {
        "hash_id": "GOST94_CRYPTOPRO",
        "ch": "0xFF",
        "msg_size": 64,
        "expected_hash": "58504D26B3677E756BA3F4A9FD2F14B3BA5457066A4AA1D700659B90DCDDD3C6"
    }
]

# int set_filename = (tests[count].hash_id == RHASH_BTIH);
# assert_rep_hash(tests[count].hash_id, 'a', 10000, tests[count].expected_hash, set_filename);

def make_tis_test_long_strings(case_no, machdep):
    test_hashes_C_path = path.join("librhash", "test_hashes.c")
    test = make_librhash_test("test_long_strings", machdep)
    test["name"] = "%s : %s : CASE %d, %s" % (test_hashes_C_path, "test_long_strings", case_no, machdep["pretty_name"])
    test["main"] = "tis_test_long_strings"
    # macros
    case = long_strings_tests[case_no]
    hash_id = "RHASH_" + case["hash_id"]
    hash_name = "\\\"" + case["hash_id"] + "\\\""
    if "set_filename" in case and case["set_filename"]:
        set_filename = 1
    else:
        set_filename = 0
    if "ch" in case:
        ch = case["ch"];
    else:
        ch = "%d" % ord('a');
    if "msg_size" in case:
        msg_size = case["msg_size"];
    else:
        msg_size = 10000;
    expected_hash = "\\\"" + case["expected_hash"] + "\\\""
    test["cpp-extra-args"] = [
        "-DTEST_LONG_STRINGS",
        "-DCASE_NO=%d" % case_no,
        "-DHASH_ID=%s" % hash_id,
        "-DHASH_NAME=%s" % hash_name,
        "-DSET_FILENAME=%d" % set_filename,
        "-DCH=%s" % ch,
        "-DMSG_SIZE=%d" % msg_size,
        "-DEXPECTED_HASH=%s" % expected_hash,
    ]

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
            product(list(range(0, len(long_strings_tests))), machdeps)
        ))
    )

tis_config = make_tis_config()
with open("tis.config", "w") as file:
    print("5. Generate the 'tis.config' file.")
    file.write(tis.string_of_json(tis_config))
