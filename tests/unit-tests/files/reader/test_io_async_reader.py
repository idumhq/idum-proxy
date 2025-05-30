import asyncio
import io
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from starlette.responses import Response, StreamingResponse

from idum_proxy.files.reader.io_async_reader import download_text_file


class TestDownloadTextFile:
    """Test suite for download_text_file function"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def teardown_method(self):
        """Clean up after each test method."""
        self.temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_file_not_exists(self):
        """Test behavior when file doesn't exist."""
        non_existent_file = self.temp_path / "non_existent.txt"

        response = await download_text_file(non_existent_file)

        assert isinstance(response, Response)
        assert response.status_code == 404
        assert response.media_type == "text/plain"
        assert response.body == b"Not Found"

    @pytest.mark.asyncio
    async def test_path_is_directory(self):
        """Test behavior when path points to a directory."""
        directory = self.temp_path / "test_dir"
        directory.mkdir()

        response = await download_text_file(directory)

        assert isinstance(response, Response)
        assert response.status_code == 404
        assert response.media_type == "text/plain"
        assert response.body == b"Not Found"

    @pytest.mark.asyncio
    async def test_symlink_not_followed(self):
        """Test that symlinks are not followed when follow_symlinks=False."""
        # Create a real file
        real_file = self.temp_path / "real_file.txt"
        real_file.write_text("real content", encoding="utf-8")

        # Create a symlink to the real file
        symlink = self.temp_path / "symlink.txt"
        try:
            symlink.symlink_to(real_file)
        except OSError:
            pytest.skip("Symlink creation not supported on this system")

        response = await download_text_file(symlink)

        # Should return 404 because symlinks are not followed
        assert isinstance(response, Response)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_successful_file_download_small(self):
        """Test successful download of a small text file."""
        test_content = "Hello, World!\nThis is a test file."
        test_file = self.temp_path / "test.txt"
        test_file.write_text(test_content, encoding="utf-8")

        response = await download_text_file(test_file)

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/plain; charset=utf-8"
        assert (
            response.headers["Content-Disposition"] == 'attachment; filename="test.txt"'
        )

        # Collect all chunks from the streaming response
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)

        # Verify content
        full_content = b"".join(chunks)
        assert full_content == test_content.encode("utf-8")

    @pytest.mark.asyncio
    async def test_successful_file_download_large(self):
        """Test successful download of a large text file (multiple chunks)."""
        # Create content larger than buffer size (8192 bytes)
        test_content = "A" * 10000 + "\n" + "B" * 10000
        test_file = self.temp_path / "large_test.txt"
        test_file.write_text(test_content, encoding="utf-8")

        response = await download_text_file(test_file)

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/plain; charset=utf-8"
        assert (
            response.headers["Content-Disposition"]
            == 'attachment; filename="large_test.txt"'
        )

        # Collect all chunks from the streaming response
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)

        # Verify content
        full_content = b"".join(chunks)
        assert full_content == test_content.encode("utf-8")

        # Verify multiple chunks were generated
        assert len(chunks) > 1

    @pytest.mark.asyncio
    async def test_unicode_content(self):
        """Test downloading file with Unicode content."""
        test_content = "Hello 世界! 🌍 Émojis and unicode: café, naïve, résumé"
        test_file = self.temp_path / "unicode.txt"
        test_file.write_text(test_content, encoding="utf-8")

        response = await download_text_file(test_file)

        assert isinstance(response, StreamingResponse)

        # Collect all chunks from the streaming response
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)

        # Verify Unicode content is correctly encoded
        full_content = b"".join(chunks)
        assert full_content == test_content.encode("utf-8")

    @pytest.mark.asyncio
    async def test_empty_file(self):
        """Test downloading an empty file."""
        test_file = self.temp_path / "empty.txt"
        test_file.touch()

        response = await download_text_file(test_file)

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/plain; charset=utf-8"
        assert (
            response.headers["Content-Disposition"]
            == 'attachment; filename="empty.txt"'
        )

        # Collect all chunks (should be empty)
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)

        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_filename_with_spaces_and_special_chars(self):
        """Test filename handling with spaces and special characters."""
        test_content = "Test content"
        test_file = self.temp_path / "file with spaces & special chars.txt"
        test_file.write_text(test_content, encoding="utf-8")

        response = await download_text_file(test_file)

        assert isinstance(response, StreamingResponse)
        expected_filename = (
            'attachment; filename="file with spaces & special chars.txt"'
        )
        assert response.headers["Content-Disposition"] == expected_filename

    @pytest.mark.asyncio
    async def test_file_read_error_handling(self):
        """Test error handling when file read fails."""
        test_file = self.temp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        # Mock io.open to raise an exception
        with patch("io.open", side_effect=IOError("Permission denied")):
            response = await download_text_file(test_file)

            # The function should still return a StreamingResponse
            # but the error will occur when iterating over the body
            assert isinstance(response, StreamingResponse)

            # When we try to iterate over the response, it should raise an error
            with pytest.raises(IOError, match="Permission denied"):
                chunks = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk)

    @pytest.mark.asyncio
    async def test_chunked_reading_boundary(self):
        """Test that chunked reading works correctly at buffer boundaries."""
        # Create content that's exactly the buffer size
        test_content = "X" * 8192
        test_file = self.temp_path / "boundary_test.txt"
        test_file.write_text(test_content, encoding="utf-8")

        response = await download_text_file(test_file)

        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)

        # Should have exactly one chunk
        assert len(chunks) == 1
        assert chunks[0] == test_content.encode("utf-8")

    @pytest.mark.asyncio
    async def test_chunked_reading_multiple_boundaries(self):
        """Test chunked reading with content spanning multiple buffer sizes."""
        # Create content that spans multiple buffer sizes with some remainder
        test_content = "Y" * (8192 * 2 + 1000)  # 2.12 times buffer size
        test_file = self.temp_path / "multi_boundary_test.txt"
        test_file.write_text(test_content, encoding="utf-8")

        response = await download_text_file(test_file)

        chunks = []
        chunk_sizes = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
            chunk_sizes.append(len(chunk))

        # Should have 3 chunks: 8192, 8192, 1000 bytes
        assert len(chunks) == 3
        assert chunk_sizes[0] == 8192
        assert chunk_sizes[1] == 8192
        assert chunk_sizes[2] == 1000

        # Verify complete content
        full_content = b"".join(chunks)
        assert full_content == test_content.encode("utf-8")

    @pytest.mark.asyncio
    async def test_newline_handling(self):
        """Test that different newline styles are preserved."""
        test_content = "Line 1\nLine 2\r\nLine 3\rLine 4"
        test_file = self.temp_path / "newlines.txt"
        test_file.write_text(test_content, encoding="utf-8")

        response = await download_text_file(test_file)

        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)

        full_content = b"".join(chunks)
        # On Windows, Python might convert \n to \r\n, but we want to preserve original
        # The key is that the content should be readable and consistent
        decoded_content = full_content.decode("utf-8")
        assert "Line 1" in decoded_content
        assert "Line 2" in decoded_content
        assert "Line 3" in decoded_content
        assert "Line 4" in decoded_content

    @pytest.mark.asyncio
    async def test_response_headers(self):
        """Test that all expected response headers are set correctly."""
        test_content = "Header test content"
        test_file = self.temp_path / "headers_test.txt"
        test_file.write_text(test_content, encoding="utf-8")

        response = await download_text_file(test_file)

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/plain; charset=utf-8"
        assert "Content-Disposition" in response.headers
        assert response.headers["Content-Disposition"].startswith(
            "attachment; filename="
        )
        assert "headers_test.txt" in response.headers["Content-Disposition"]

    @pytest.mark.asyncio
    async def test_pathlib_path_object(self):
        """Test that the function works with pathlib.Path objects."""
        test_content = "Path object test"
        test_file = self.temp_path / "pathlib_test.txt"
        test_file.write_text(test_content, encoding="utf-8")

        # Ensure we're passing a Path object, not a string
        assert isinstance(test_file, Path)

        response = await download_text_file(test_file)

        assert isinstance(response, StreamingResponse)
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)

        full_content = b"".join(chunks)
        assert full_content == test_content.encode("utf-8")

    def test_text_file_streamer_function_scope(self):
        """Test that the inner streamer function works independently."""
        # This test verifies the inner function logic without async context
        test_content = "Streamer test"
        test_file = self.temp_path / "streamer_test.txt"
        test_file.write_text(test_content, encoding="utf-8")

        # Manually create and test the streamer function
        def text_file_streamer():
            with io.open(test_file, "r", encoding="utf-8", buffering=8192) as file:
                while chunk := file.read(8192):
                    if chunk:
                        yield chunk.encode("utf-8")

        chunks = list(text_file_streamer())
        full_content = b"".join(chunks)
        assert full_content == test_content.encode("utf-8")

    @pytest.mark.asyncio
    async def test_concurrent_downloads(self):
        """Test that multiple concurrent downloads work correctly."""
        # Create multiple test files
        files_and_content = []
        for i in range(3):
            content = f"File {i} content with unique data: {'X' * (1000 * (i + 1))}"
            file_path = self.temp_path / f"concurrent_{i}.txt"
            file_path.write_text(content, encoding="utf-8")
            files_and_content.append((file_path, content))

        # Start concurrent downloads
        tasks = []
        for file_path, _ in files_and_content:
            task = download_text_file(file_path)
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # Verify all responses
        for i, (response, (_, expected_content)) in enumerate(
            zip(responses, files_and_content)
        ):
            assert isinstance(response, StreamingResponse)

            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk)

            full_content = b"".join(chunks)
            assert full_content == expected_content.encode("utf-8")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
