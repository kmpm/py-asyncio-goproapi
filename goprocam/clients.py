import asyncio
import aiohttp
import os
import json
import posixpath
from os import path
try:
    from urlparse import urlsplit
    from urllib import unquote
except ImportError:  # Python 3
    from urllib.parse import urlsplit, unquote

from .errors import HttpError, GoProError, GoProConnectionError

__all__ = ['AsyncClient']


class AsyncClient:
    def __init__(self, working_path=None, **kwargs):
        self._session = None
        self.download_semaphore = asyncio.Semaphore(kwargs.pop('download_semaphore', 4))
        self.chunk_size = kwargs.pop('chunk_size', 64 * 1024)
        self.working_path = working_path

    def session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session

    async def quit(self):
        if self.session:
            await self._session.close()
            self._session = None

    async def getText(self, url, timeout=30):
        try:
            async with self.session().get(url, timeout=timeout) as resp:
                if resp.status == 200:
                    return await resp.text()
                message = await resp.text()
                try:
                    message = json.loads(message.replace("\r\n", "").replace("\n", ""))
                    raise GoProError(resp.status, resp.reason, message)
                except json.JSONDecodeError:
                    print('error', message)
                    raise HttpError(resp.status, resp.reason)
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise GoProConnectionError('Can not connect', err)

    async def getJSON(self, url, timeout=30):
        async with self.session().get(url, timeout=timeout) as resp:
            return await resp.json()

    async def download(self, url, filename=None):
        async with self.download_semaphore:
            if not filename:
                filename = url2filename(url)

            if self.working_path:
                filename = path.join(self.working_path, filename)

            async with self.session().get(url) as resp:
                with open(filename, 'wb') as fd:
                    while True:
                        chunk = await resp.content.read(self.chunk_size)
                        if not chunk:
                            break
                        fd.write(chunk)


def url2filename(url):
    """Return basename corresponding to url.
    >>> print(url2filename('http://example.com/path/to/file%C3%80?opt=1'))
    fileÀ
    >>> print(url2filename('http://example.com/slash%2fname')) # '/' in name
    Traceback (most recent call last):
    ...
    ValueError
    """
    urlpath = urlsplit(url).path
    basename = posixpath.basename(unquote(urlpath))
    if (
        os.path.basename(basename) != basename or
        unquote(posixpath.basename(urlpath)) != basename
    ):
        raise ValueError  # reject '%2f' or 'dir%5Cbasename.ext' on Windows
    return basename
