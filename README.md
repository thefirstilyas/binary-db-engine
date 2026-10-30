# Custom Binary Database Engine

A low-level custom database management system implemented in Python, featuring custom binary encoding, internal memory management, and a dedicated CLI query interface.

##  Overview

This project implements a binary storage engine from scratch without external database dependencies. It manages data directly at the byte level, optimizing record allocation, string storage, and memory reuse through custom data structures.

##  Key Features

* **Custom Binary Encoding:** Direct binary serialization/deserialization for structured records and metadata header management.
* **Efficient Memory Reuse (Freelist):** Implements a freelist mechanism to reclaim and reuse deleted memory blocks efficiently.
* **Doubly-Linked Entry Architecture:** Fast traversal and record management via doubly-linked structures inside the binary file.
* **String Buffers & Variable Length Storage:** Optimized storage for variable-length strings and attributes.
* **CLI Query Interpreter:** Command-line interface allowing interactive database operations, querying, and execution of `.uldb` script files.

##  Repository Structure

```text
.
├── database.py       # Core database management logic and API
├── binary.py         # Low-level binary encoding, headers, and serialization
├── uldb.py           # CLI query interpreter and command execution
├── script.uldb       # Sample query script file
├── test.py           # Unit tests and system validation
└── README.md         # Project documentation