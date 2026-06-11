import pytest
import os
import tempfile
from services.log_parser import parse_log_file, merge_dataframes


APACHE_LOG = '''\
192.168.1.100 - frank [10/Oct/2000:13:55:36 -0700] "GET /index.html HTTP/1.1" 200 2326
10.0.0.1 - - [10/Oct/2000:13:56:00 -0700] "POST /login HTTP/1.1" 401 512
192.168.1.200 - - [10/Oct/2000:13:57:00 -0700] "GET /admin HTTP/1.1" 403 256
'''

SYSLOG_LOG = '''\
Jan 10 09:30:00 hostname sshd[1234]: Failed password for root from 192.168.1.1 port 22 ssh2
Jan 10 09:30:05 hostname sshd[1234]: Failed password for admin from 192.168.1.1 port 22 ssh2
Jan 10 09:31:00 hostname sshd[1234]: Accepted password for user1 from 10.0.0.5 port 2345 ssh2
'''

GENERIC_LOG = '''\
2024-01-10 09:30:00 ERROR Failed to authenticate user admin from 192.168.1.50
2024-01-10 09:30:01 INFO User login successful: operator from 10.0.0.1
2024-01-10 09:30:02 WARNING access denied for /admin resource
'''

CEF_LOG = '''\
CEF:0|SecurityVendor|IDS|1.0|100|SQL Injection Detected|8|src=192.168.1.10 dst=10.0.0.1 request=/search?q=union+select
CEF:0|SecurityVendor|IDS|1.0|101|Path Traversal|7|src=192.168.1.20 dst=10.0.0.1 request=/files/../etc/passwd
'''


def _write_temp(content: str, suffix: str = ".log") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_parse_apache_log():
    path = _write_temp(APACHE_LOG, ".log")
    try:
        df = parse_log_file(path)
        assert not df.empty
        assert len(df) == 3
        assert "source_ip" in df.columns
        assert "192.168.1.100" in df["source_ip"].values
    finally:
        os.remove(path)


def test_parse_syslog():
    path = _write_temp(SYSLOG_LOG, ".syslog")
    try:
        df = parse_log_file(path)
        assert not df.empty
        assert len(df) == 3
    finally:
        os.remove(path)


def test_parse_generic_log():
    path = _write_temp(GENERIC_LOG, ".log")
    try:
        df = parse_log_file(path)
        assert not df.empty
        assert len(df) == 3
        assert any("ERROR" in str(r) for r in df["level"].values)
    finally:
        os.remove(path)


def test_parse_cef_log():
    path = _write_temp(CEF_LOG, ".cef")
    try:
        df = parse_log_file(path)
        assert not df.empty
        assert len(df) == 2
    finally:
        os.remove(path)


def test_parse_empty_file():
    path = _write_temp("", ".log")
    try:
        df = parse_log_file(path)
        assert df.empty
    finally:
        os.remove(path)


def test_merge_dataframes():
    path1 = _write_temp(APACHE_LOG, ".log")
    path2 = _write_temp(GENERIC_LOG, ".log")
    try:
        df1 = parse_log_file(path1)
        df2 = parse_log_file(path2)
        merged = merge_dataframes(df1, df2)
        assert len(merged) == len(df1) + len(df2)
    finally:
        os.remove(path1)
        os.remove(path2)


def test_merge_with_empty():
    path = _write_temp(APACHE_LOG, ".log")
    try:
        df = parse_log_file(path)
        import pandas as pd
        merged = merge_dataframes(pd.DataFrame(), df)
        assert len(merged) == len(df)
    finally:
        os.remove(path)
