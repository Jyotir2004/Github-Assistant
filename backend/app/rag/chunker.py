import os
from typing import List, Dict, Any

class CodeChunker:
    def __init__(self, chunk_lines: int = 50, overlap_lines: int = 10, max_chunk_chars: int = 2500):
        self.chunk_lines = chunk_lines
        self.overlap_lines = overlap_lines
        self.max_chunk_chars = max_chunk_chars

    def chunk_file(self, file_path: str, content: str, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        Splits file content into overlapping line-based chunks with metadata.
        """
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        # If file is short enough, return as single chunk
        if total_lines <= self.chunk_lines and len(content) <= self.max_chunk_chars:
            return [{
                "chunk_id": f"{owner}_{repo}_{file_path.replace('/', '__')}_0",
                "content": content,
                "metadata": {
                    "owner": owner,
                    "repo": repo,
                    "file_path": file_path,
                    "chunk_index": 0,
                    "start_line": 1,
                    "end_line": max(1, total_lines),
                    "total_lines": total_lines,
                    "extension": os.path.splitext(file_path)[1]
                }
            }]

        chunks = []
        start_idx = 0
        chunk_idx = 0

        while start_idx < total_lines:
            end_idx = min(start_idx + self.chunk_lines, total_lines)
            chunk_slice = lines[start_idx:end_idx]
            chunk_text = "".join(chunk_slice)

            # If chunk is still too long in characters, trim line count
            while len(chunk_text) > self.max_chunk_chars and (end_idx - start_idx) > 10:
                end_idx -= 5
                chunk_slice = lines[start_idx:end_idx]
                chunk_text = "".join(chunk_slice)

            chunk_id = f"{owner}_{repo}_{file_path.replace('/', '__')}_{chunk_idx}"
            chunks.append({
                "chunk_id": chunk_id,
                "content": chunk_text,
                "metadata": {
                    "owner": owner,
                    "repo": repo,
                    "file_path": file_path,
                    "chunk_index": chunk_idx,
                    "start_line": start_idx + 1,
                    "end_line": end_idx,
                    "total_lines": total_lines,
                    "extension": os.path.splitext(file_path)[1]
                }
            })

            chunk_idx += 1
            if end_idx >= total_lines:
                break
            # Step forward with overlap
            start_idx = max(start_idx + 1, end_idx - self.overlap_lines)

        return chunks
