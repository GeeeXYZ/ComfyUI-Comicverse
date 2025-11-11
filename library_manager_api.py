"""
Library Manager API for ComicVerse custom nodes.

Provides REST API endpoints for managing prompt library JSON files:
- List all libraries
- Read library content
- Create new library
- Save/update library
- Rename library
- Delete library
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict

from aiohttp import web

try:
    from server import PromptServer
except ImportError:  # pragma: no cover
    PromptServer = None  # type: ignore


# Import the library directory helper from prompt_loader_node
from .prompt_loader_node import _get_library_dir


def _validate_library_name(name: str) -> bool:
    """
    Validate library name to prevent path traversal and invalid characters.
    Only allow alphanumeric, underscore, hyphen, and space.
    """
    if not name or len(name) > 100:
        return False
    # Allow alphanumeric, underscore, hyphen, space, and common unicode characters
    pattern = r'^[\w\s\-]+$'
    return bool(re.match(pattern, name, re.UNICODE))


def _sanitize_library_name(name: str) -> str:
    """Remove .json extension if present and strip whitespace."""
    name = name.strip()
    if name.endswith('.json'):
        name = name[:-5]
    return name


# Register API routes if PromptServer is available
if PromptServer is not None:
    routes = PromptServer.instance.routes

    @routes.get("/comicverse/libraries/list")
    async def list_libraries(request: web.Request) -> web.Response:
        """List all available library JSON files."""
        try:
            library_dir = _get_library_dir()
            
            if not library_dir.exists():
                library_dir.mkdir(parents=True, exist_ok=True)
                return web.json_response({"libraries": []})
            
            json_files = sorted(library_dir.glob("*.json"))
            libraries = [
                {
                    "name": f.stem,
                    "filename": f.name,
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime,
                }
                for f in json_files
            ]
            
            return web.json_response({"libraries": libraries})
        
        except Exception as e:
            return web.json_response(
                {"error": f"Failed to list libraries: {str(e)}"},
                status=500
            )

    @routes.get("/comicverse/libraries/read")
    async def read_library(request: web.Request) -> web.Response:
        """Read the content of a specific library file."""
        try:
            name = request.query.get("name", "").strip()
            if not name:
                return web.json_response(
                    {"error": "Library name is required"},
                    status=400
                )
            
            name = _sanitize_library_name(name)
            if not _validate_library_name(name):
                return web.json_response(
                    {"error": "Invalid library name"},
                    status=400
                )
            
            library_dir = _get_library_dir()
            library_path = library_dir / f"{name}.json"
            
            if not library_path.exists():
                return web.json_response(
                    {"error": f"Library '{name}' not found"},
                    status=404
                )
            
            # Read raw content
            content = library_path.read_text(encoding="utf-8")
            
            # Parse to validate JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                return web.json_response(
                    {"error": f"Invalid JSON in library file: {str(e)}"},
                    status=500
                )
            
            return web.json_response({
                "name": name,
                "content": content,
                "data": data,
            })
        
        except Exception as e:
            return web.json_response(
                {"error": f"Failed to read library: {str(e)}"},
                status=500
            )

    @routes.post("/comicverse/libraries/create")
    async def create_library(request: web.Request) -> web.Response:
        """Create a new library file with empty array."""
        try:
            data = await request.json()
            name = data.get("name", "").strip()
            
            if not name:
                return web.json_response(
                    {"error": "Library name is required"},
                    status=400
                )
            
            name = _sanitize_library_name(name)
            if not _validate_library_name(name):
                return web.json_response(
                    {"error": "Invalid library name. Use only letters, numbers, spaces, hyphens, and underscores."},
                    status=400
                )
            
            library_dir = _get_library_dir()
            library_dir.mkdir(parents=True, exist_ok=True)
            
            library_path = library_dir / f"{name}.json"
            
            if library_path.exists():
                return web.json_response(
                    {"error": f"Library '{name}' already exists"},
                    status=409
                )
            
            # Create with empty array
            initial_content = data.get("content", "[]")
            
            # Validate JSON
            try:
                parsed = json.loads(initial_content)
                if not isinstance(parsed, list):
                    return web.json_response(
                        {"error": "Library content must be a JSON array"},
                        status=400
                    )
            except json.JSONDecodeError as e:
                return web.json_response(
                    {"error": f"Invalid JSON: {str(e)}"},
                    status=400
                )
            
            # Write file with pretty formatting
            library_path.write_text(
                json.dumps(parsed, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            
            return web.json_response({
                "success": True,
                "name": name,
                "message": f"Library '{name}' created successfully"
            })
        
        except Exception as e:
            return web.json_response(
                {"error": f"Failed to create library: {str(e)}"},
                status=500
            )

    @routes.post("/comicverse/libraries/save")
    async def save_library(request: web.Request) -> web.Response:
        """Save/update library content."""
        try:
            data = await request.json()
            name = data.get("name", "").strip()
            content = data.get("content", "")
            
            if not name:
                return web.json_response(
                    {"error": "Library name is required"},
                    status=400
                )
            
            name = _sanitize_library_name(name)
            if not _validate_library_name(name):
                return web.json_response(
                    {"error": "Invalid library name"},
                    status=400
                )
            
            library_dir = _get_library_dir()
            library_path = library_dir / f"{name}.json"
            
            if not library_path.exists():
                return web.json_response(
                    {"error": f"Library '{name}' not found"},
                    status=404
                )
            
            # Validate JSON
            try:
                parsed = json.loads(content)
                if not isinstance(parsed, list):
                    return web.json_response(
                        {"error": "Library content must be a JSON array"},
                        status=400
                    )
            except json.JSONDecodeError as e:
                return web.json_response(
                    {"error": f"Invalid JSON: {str(e)}"},
                    status=400
                )
            
            # Create backup
            backup_path = library_dir / f"{name}.json.backup"
            if library_path.exists():
                backup_path.write_bytes(library_path.read_bytes())
            
            # Write file with pretty formatting
            library_path.write_text(
                json.dumps(parsed, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            
            return web.json_response({
                "success": True,
                "name": name,
                "message": f"Library '{name}' saved successfully"
            })
        
        except Exception as e:
            return web.json_response(
                {"error": f"Failed to save library: {str(e)}"},
                status=500
            )

    @routes.post("/comicverse/libraries/rename")
    async def rename_library(request: web.Request) -> web.Response:
        """Rename a library file."""
        try:
            data = await request.json()
            old_name = data.get("old_name", "").strip()
            new_name = data.get("new_name", "").strip()
            
            if not old_name or not new_name:
                return web.json_response(
                    {"error": "Both old_name and new_name are required"},
                    status=400
                )
            
            old_name = _sanitize_library_name(old_name)
            new_name = _sanitize_library_name(new_name)
            
            if not _validate_library_name(old_name) or not _validate_library_name(new_name):
                return web.json_response(
                    {"error": "Invalid library name"},
                    status=400
                )
            
            if old_name == new_name:
                return web.json_response(
                    {"error": "New name must be different from old name"},
                    status=400
                )
            
            library_dir = _get_library_dir()
            old_path = library_dir / f"{old_name}.json"
            new_path = library_dir / f"{new_name}.json"
            
            if not old_path.exists():
                return web.json_response(
                    {"error": f"Library '{old_name}' not found"},
                    status=404
                )
            
            if new_path.exists():
                return web.json_response(
                    {"error": f"Library '{new_name}' already exists"},
                    status=409
                )
            
            # Rename file
            old_path.rename(new_path)
            
            return web.json_response({
                "success": True,
                "old_name": old_name,
                "new_name": new_name,
                "message": f"Library renamed from '{old_name}' to '{new_name}'"
            })
        
        except Exception as e:
            return web.json_response(
                {"error": f"Failed to rename library: {str(e)}"},
                status=500
            )

    @routes.post("/comicverse/libraries/delete")
    async def delete_library(request: web.Request) -> web.Response:
        """Delete a library file."""
        try:
            data = await request.json()
            name = data.get("name", "").strip()
            
            if not name:
                return web.json_response(
                    {"error": "Library name is required"},
                    status=400
                )
            
            name = _sanitize_library_name(name)
            if not _validate_library_name(name):
                return web.json_response(
                    {"error": "Invalid library name"},
                    status=400
                )
            
            library_dir = _get_library_dir()
            library_path = library_dir / f"{name}.json"
            
            if not library_path.exists():
                return web.json_response(
                    {"error": f"Library '{name}' not found"},
                    status=404
                )
            
            # Create backup before deletion
            backup_path = library_dir / f"{name}.json.deleted"
            backup_path.write_bytes(library_path.read_bytes())
            
            # Delete file
            library_path.unlink()
            
            return web.json_response({
                "success": True,
                "name": name,
                "message": f"Library '{name}' deleted successfully (backup saved as {name}.json.deleted)"
            })
        
        except Exception as e:
            return web.json_response(
                {"error": f"Failed to delete library: {str(e)}"},
                status=500
            )



