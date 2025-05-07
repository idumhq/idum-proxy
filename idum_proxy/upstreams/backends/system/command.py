import asyncio
import logging
import pty
import struct
import os

import fcntl
import termios
from http import HTTPStatus
import aiofiles
from starlette.requests import Request
from starlette.responses import StreamingResponse, JSONResponse, Response

from idum_proxy.config.models import Endpoint, Backends


class Command:
    """Command execution client for running system commands asynchronously."""

    def __init__(self, connection_pooling, endpoint: Endpoint, backend: Backends):
        self.connection_pooling = connection_pooling
        self.endpoint = endpoint
        self.backend = backend
        self.buffer_size = 4096
        self.timeout = 10

    async def handle_request(self, request: Request, headers: dict) -> Response:
        """Execute a command and return its output.

        Args:
            command: The command to execute

        Returns:
            Response object containing command output and status
        """
        try:
            command = self.backend.command.command
            logging.info(f"Executing command: {command}")
            env = os.environ.copy()
            env.update({"PYTHONUNBUFFERED": "1", "TERM": "xterm-256color"})

            # Handle streaming response
            async def stream_output():
                master, slave = pty.openpty()

                # Set terminal size to ensure proper behavior
                term_size = struct.pack("HHHH", 24, 80, 0, 0)
                fcntl.ioctl(slave, termios.TIOCSWINSZ, term_size)

                # Start process with the slave end of pty as stdout/stderr
                p1 = await asyncio.create_subprocess_shell(
                    command,
                    stdout=slave,
                    stderr=slave,
                    stdin=asyncio.subprocess.PIPE,
                    close_fds=False,
                    env=env,
                )

                # Close the slave end in this process
                os.close(slave)

                # Set non-blocking mode on the master end
                fl = fcntl.fcntl(master, fcntl.F_GETFL)
                fcntl.fcntl(master, fcntl.F_SETFL, fl | os.O_NONBLOCK)

                # Read from the master end in a loop
                async with aiofiles.open(master, "rb") as file:
                    while True:
                        try:
                            # data = await aiofiles.open(master)
                            # data = os.read(master, self.buffer_size)
                            # if data:
                            data = await file.read(self.buffer_size)
                            if data:
                                yield data
                            else:
                                await asyncio.sleep(0.1)
                        except BlockingIOError:
                            await asyncio.sleep(0.1)
                        except OSError:
                            break

                        # Check if process is still running
                        if p1.returncode is not None:
                            break

                """
                try:
                    os.close(master)
                except OSError:
                    pass
                """

                await p1.wait()

            return StreamingResponse(stream_output())

        except asyncio.TimeoutError:
            logging.error(f"Command execution timed out after {self.timeout}s")
            return JSONResponse(
                content={"error": f"Command execution timed out after {self.timeout}s"},
                status_code=HTTPStatus.REQUEST_TIMEOUT.value,
            )
        except Exception as e:
            logging.error(f"Unexpected error executing command: {str(e)}")
            return JSONResponse(
                content={"error": str(e)},
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
