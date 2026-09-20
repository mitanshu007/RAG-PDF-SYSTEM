"""Compatibility module for running ``uvicorn main:app`` during development."""

from reg.app import app, main

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()
