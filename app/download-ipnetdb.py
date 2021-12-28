#!/usr/bin/env python3
'''

    Downloads the IPNetDB databases to a local directory.

    Usage:
    $ ./download-ipnetdb.py --save-to /some/local/directory

'''


IPNETDB_LATEST_INDEX = 'https://ipnetdb.com/latest.json'


import sys
import os
import argparse
import logging
import json
import hashlib
import shutil
from urllib.parse import urlsplit
from pathlib import Path
from datetime import datetime
import requests


def get_logger(name, level=logging.INFO):
    log = logging.getLogger(name)
    log.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    fmt = logging.Formatter('%(asctime)s %(name)s [%(levelname)s] %(message)s')
    ch.setFormatter(fmt)
    log.addHandler(ch)
    return log


log = get_logger('downloader')


def get_index(index_url):
    return requests.get(
        index_url,
        headers={'User-Agent': 'IPNetDB Service'},
        timeout=10
    ).json()


def get_index_file(index_file):
    if not index_file.is_file():
        raise Exception(f'Index file does not exist: {index_file}')
    with index_file.open() as f:
        j = json.loads(f.read())
    return j


def parse_date(datestr):
    try:
        return datetime.strptime(str(datestr), '%Y-%m-%d')
    except Exception:
        return datetime(year=1970, month=1, day=1)


_allowed_filename_chars = (
    'abcdefghijklmnopqrstuvwxyz'
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    '0123456789'
    '-_.'
)


_allowed_hex_chars = (
    'abcdef'
    '0123456789'
)


def validate_index(index):
    # Basic key and type checks
    filename = index.get('file', '')
    if not filename:
        raise Exception('Index has no "file" set: {index}')
    if not isinstance(filename, str):
        raise Exception(f'index[file] must be a str, got: {type(filename)}')
    url = index.get('url', '')
    if not url:
        raise Exception('Index has no "url" set: {index}')
    if not isinstance(url, str):
        raise Exception(f'index[url] must be a str, got: {type(url)}')
    date = index.get('date', '')
    if not date:
        raise Exception('Index has no "date" set: {index}')
    if not isinstance(date, str):
        raise Exception(f'index[url] must be a str, got: {type(date)}')
    sha256 = index.get('sha256', '')
    if not sha256:
        raise Exception('Index has no "sha256" set: {index}')
    if not isinstance(sha256, str):
        raise Exception(f'index[sha256] must be a str, got: {type(sha256)}')
    bytesize = index.get('bytes', 0)
    if bytesize == 0:
        raise Exception('Index has no "bytesize" set: {index}')
    if not isinstance(bytesize, int):
        raise Exception(f'index[bytes] must be a int, got: {type(bytesize)}')
    # Validate the filename
    for c in filename:
        if c not in _allowed_filename_chars:
            raise Exception(f'index[file] contains unknown chars: {filename}')
    if '..' in filename:
        raise Exception(f'index[file] contains double dots: {filename}')
    if len(filename) > 256:
        raise Exception(f'index[file] is longer than 256 chars: {filename}')
    # Validate the URL:
    url_parts = urlsplit(url)
    if url_parts.scheme.lower() != 'https':
        raise Exception(f'index[url] does not have a HTTPS scheme: {url}')
    if not url_parts.netloc.endswith('.ipnetdb.net'):
        raise Exception(f'index[url] does not end in .ipnetdb.net: {url}')
    if not url_parts.path:
        raise Exception(f'index[url] has no path: {url}')
    # Validate the date
    parsed_date = parse_date(date)
    if parsed_date == datetime(year=1970, month=1, day=1):
        raise Exception(f'index[date] failed to parse: {date}')
    # Validate the sha256
    if len(sha256) != 64:
        raise Exception(f'index[sha256] is not 64 chars in length: {sha256}')
    for c in sha256:
        if c not in _allowed_hex_chars:
            raise Exception(f'index[sha256] contains unknown chars: {sha256}')
    # validate the byte size
    if bytesize <= 1024:
        raise Exception(f'index[bytes] is too small: {bytesize}')
    if bytesize >= 1073741824:
        raise Exception(f'index[bytes] is too big: {bytesize}')
    # All OK
    return True


def get_file_hash(filepath, algo=hashlib.sha256):
    def _chunked(f):
        chunk_size = 1024 * 1024  # 1mb
        while True:
            chunk = f.read(chunk_size)
            if chunk:
                yield chunk
            else:
                return
    h = algo()
    with open(filepath, 'rb') as f:
        for chunk in _chunked(f):
            h.update(chunk)
    return h.hexdigest()


def download_file(url, to_path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(to_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)
    return Path(to_path).is_file()


def update_available(save_to, local_index, remote_index):
    local_file = local_index.get('file', '')
    local_path = save_to / local_file
    local_date = parse_date(local_index.get('date', ''))
    local_sha256 = local_index.get('sha256', '')
    remote_url = remote_index.get('url', '')
    remote_date = parse_date(remote_index.get('date', ''))
    remote_sha256 = remote_index.get('sha256', '')
    if not local_path.is_file():
        if remote_url:
            log.info(f'Local database "{local_file}" does not exist and '
                     f'remote URL is set: {remote_url} - updating')
            return True
        else:
            log.info(f'Local database "{local_file}" does not exist but '
                     f'remote URL is not set - not updating')
            return False
    local_file_hash = get_file_hash(str(local_path))
    if local_file_hash != local_sha256:
        if remote_url:
            log.info(f'Actual local database {local_path} has '
                     f'{local_file_hash} does notmatch the local index hash '
                     f'{local_sha256} and remote URL is set: {remote_url} '
                     f' - updating')
            return True
            log.info(f'Actual local database {local_path} has '
                     f'{local_file_hash} does not match the local index hash '
                     f'{local_sha256} but remote URL is not set '
                     f'- not updating')
            return False
        return True if remote_url else False
    if local_sha256 == remote_sha256:
        log.info(f'Local index hash and remote index hash match for '
                 f'{local_file} with {remote_sha256} - not updating')
        return False
    if remote_date > local_date:
        log.info(f'Index hashes are different and the remote date '
                 f'{remote_date} is newer than the local date '
                 f'{local_date} for {local_file} - updating')
        return True
    else:
        return False


def download_database(save_to, index, suffix):
    remote_filename = index.get('file', '')
    url = index.get('url', '')
    sha256 = index.get('sha256')
    if not remote_filename or not url or not sha256:
        raise Exception(f'Cannot download database, index missing details: '
                        f'{index}')
    filename = f'{remote_filename}.{suffix}'
    filepath = save_to / filename
    if not download_file(url, filepath):
        raise Exception(f'Failed to download {url} to {filepath}')
    local_file_hash = get_file_hash(str(filepath))
    if local_file_hash != sha256:
        raise Exception(f'Failed to download {url}, hash mismatch '
                        f'l:{local_file_hash} != r:{sha256}')
    return filepath


def save_index(save_to, index, suffix):
    filename = f'index.json.{suffix}'
    filepath = save_to / filename
    data = json.dumps(index)
    with open(filepath, 'wb') as f:
        f.write(data.encode())
    if not filepath.is_file():
        raise Exception(f'Failed to save index to: {filepath}')
    return filepath


def move_file(path_from, path_to):
    return shutil.move(str(path_from), str(path_to))


if __name__ == '__main__':
    log.info('Refreshing IPNetDB databases')
    parser = argparse.ArgumentParser(
        description='Downloads the IPNetDB databases to a local directory.'
    )
    parser.add_argument(
        '--save-to',
        type=str,
        required=True,
        help='Local directory to save databases to'
    )
    args = parser.parse_args()
    save_to = Path(args.save_to).resolve()
    if not save_to.is_dir():
        raise Exception(f'Directory does not exist: {save_to}')
    log.info(f'Downloading to directory: {save_to}')
    local_index_file = save_to / 'index.json'
    try:
        local_index = get_index_file(local_index_file)
    except Exception as e:
        local_index = {}
    log.info(f'Fetching latest IPNetDB index: {IPNETDB_LATEST_INDEX}')
    try:
        remote_index = get_index(IPNETDB_LATEST_INDEX)
    except Exception as e:
        log.error(f'Failed to get IPNetDB index: {e}')
        sys.exit(1)
    remote_prefix_index = remote_index.get('prefix', {})
    validate_index(remote_prefix_index)
    remote_asn_index = remote_index.get('asn', {})
    validate_index(remote_asn_index)
    local_prefix_index = local_index.get('prefix', {})
    local_asn_index = local_index.get('asn', {})
    update_prefix = update_available(
        save_to,
        local_prefix_index,
        remote_prefix_index
    )
    update_asn = update_available(
        save_to,
        local_asn_index,
        remote_asn_index
    )
    prefix_update_path = None
    if update_prefix:
        log.info(f'Updating Prefix database')
        prefix_update_path = download_database(
            save_to,
            remote_prefix_index,
            'update'
        )
        log.info(f'Downloaded Prefix database update to: {prefix_update_path}')
    asn_update_path = None
    if update_asn:
        log.info(f'Updating ASN database')
        asn_update_path = download_database(
            save_to,
            remote_asn_index,
            'update'
        )
        log.info(f'Downloaded ASN database update to: {asn_update_path}')
    index_path = None
    if update_prefix or update_asn:
        log.info(f'Updating local index')
        update_index_path = save_index(save_to, remote_index, 'update')
        log.info(f'Saved updated index to: {index_path}')
        log.info(f'New database updates downloaded, deploying')
        if prefix_update_path:
            prefix_database_file = remote_prefix_index.get('file', '')
            prefix_database_path = save_to / prefix_database_file
            log.info(f'Renaming {prefix_update_path} to '
                     f'{prefix_database_path}')
            move_file(prefix_update_path, prefix_database_path)
            os.chmod(prefix_database_path, 0o644)
        if asn_update_path:
            asn_database_file = remote_asn_index.get('file', '')
            asn_database_path = save_to / asn_database_file
            log.info(f'Renaming {asn_update_path} to '
                     f'{asn_database_path}')
            move_file(asn_update_path, asn_database_path)
            os.chmod(asn_database_path, 0o644)
        index_path = save_to / 'index.json'
        log.info(f'Renaming {update_index_path} to {index_path}')
        move_file(update_index_path, index_path)
        os.chmod(index_path, 0o644)
    index = get_index_file(local_index_file)
    prefix_index = index.get('prefix', {})
    asn_index = index.get('asn', {})
    prefix_file = prefix_index.get('file', '')
    prefix_date = prefix_index.get('date', '')
    prefix_hash = prefix_index.get('sha256', '')
    asn_file = asn_index.get('file', '')
    asn_date = asn_index.get('date', '')
    asn_hash = asn_index.get('sha256', '')
    prefix_path = save_to / prefix_file
    asn_path = save_to / asn_file
    log.info(f'IPNetDB index file stored at:   {local_index_file}')
    log.info(f'IPNetDB Prefix database stored: {prefix_date} '
             f'(sha256:{prefix_hash}) at {prefix_path}')
    log.info(f'IPNetDB ASN database stored:    {asn_date} '
             f'(sha256:{asn_hash}) at {asn_path}')
    log.info(f'Done')
