"""Unified Language Configuration for the Sandbox Execution Engine."""
from typing import Dict, Optional
from pydantic import BaseModel


class LanguageConfig(BaseModel):
    id: str
    name: str
    extension: str
    default_filename: str
    docker_image: str
    compile_cmd: Optional[str] = None
    run_cmd: str
    timeout_seconds: float = 5.0
    memory_limit: str = "256m"
    pids_limit: int = 64


SUPPORTED_LANGUAGES: Dict[str, LanguageConfig] = {
    "python": LanguageConfig(
        id="python",
        name="Python",
        extension=".py",
        default_filename="main.py",
        docker_image="python:3.11-alpine",
        compile_cmd=None,
        run_cmd="python main.py",
        timeout_seconds=5.0,
        memory_limit="256m",
        pids_limit=64,
    ),
    "javascript": LanguageConfig(
        id="javascript",
        name="JavaScript (Node.js)",
        extension=".js",
        default_filename="index.js",
        docker_image="node:20-alpine",
        compile_cmd=None,
        run_cmd="node index.js",
        timeout_seconds=5.0,
        memory_limit="256m",
        pids_limit=64,
    ),
    "typescript": LanguageConfig(
        id="typescript",
        name="TypeScript",
        extension=".ts",
        default_filename="index.ts",
        docker_image="node:20-alpine",
        compile_cmd="npx -y esbuild index.ts --bundle --platform=node --outfile=dist.js",
        run_cmd="node dist.js",
        timeout_seconds=7.0,
        memory_limit="256m",
        pids_limit=64,
    ),
    "cpp": LanguageConfig(
        id="cpp",
        name="C++",
        extension=".cpp",
        default_filename="main.cpp",
        docker_image="gcc:13-alpine",
        compile_cmd="g++ -O2 -std=c++17 -o solution main.cpp",
        run_cmd="./solution",
        timeout_seconds=5.0,
        memory_limit="256m",
        pids_limit=64,
    ),
    "c": LanguageConfig(
        id="c",
        name="C",
        extension=".c",
        default_filename="main.c",
        docker_image="gcc:13-alpine",
        compile_cmd="gcc -O2 -std=c11 -o solution main.c",
        run_cmd="./solution",
        timeout_seconds=5.0,
        memory_limit="256m",
        pids_limit=64,
    ),
    "go": LanguageConfig(
        id="go",
        name="Go",
        extension=".go",
        default_filename="main.go",
        docker_image="golang:1.22-alpine",
        compile_cmd="go build -o solution main.go",
        run_cmd="./solution",
        timeout_seconds=5.0,
        memory_limit="256m",
        pids_limit=64,
    ),
    "rust": LanguageConfig(
        id="rust",
        name="Rust",
        extension=".rs",
        default_filename="main.rs",
        docker_image="rust:1.78-alpine",
        compile_cmd="rustc -O -o solution main.rs",
        run_cmd="./solution",
        timeout_seconds=7.0,
        memory_limit="256m",
        pids_limit=64,
    ),
    "java": LanguageConfig(
        id="java",
        name="Java",
        extension=".java",
        default_filename="Main.java",
        docker_image="eclipse-temurin:21-alpine",
        compile_cmd="javac Main.java",
        run_cmd="java Main",
        timeout_seconds=6.0,
        memory_limit="384m",
        pids_limit=64,
    ),
    "sql": LanguageConfig(
        id="sql",
        name="SQL (SQLite)",
        extension=".sql",
        default_filename="query.sql",
        docker_image="python:3.11-alpine",
        compile_cmd=None,
        run_cmd="sqlite3 db.sqlite < query.sql",
        timeout_seconds=4.0,
        memory_limit="256m",
        pids_limit=64,
    ),
}


def get_language_config(language_id: str) -> LanguageConfig:
    lang = language_id.lower().strip()
    if lang in SUPPORTED_LANGUAGES:
        return SUPPORTED_LANGUAGES[lang]
    raise ValueError(f"Unsupported language: '{language_id}'. Supported languages: {list(SUPPORTED_LANGUAGES.keys())}")
