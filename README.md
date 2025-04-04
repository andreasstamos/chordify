# ✨ **Chord DHT**: A Distributed Key-Value Store

## A highly scalable distributed hash table implementation with built-in replication, designed to exceed modern needs.

![Banner](/assets/banner.webp)

## 🚀 Introduction

**Chord DHT** is a production-grade implementation of the [Chord protocol](https://pdos.csail.mit.edu/papers/chord:sigcomm01/chord_sigcomm.pdf) — a classic, proven approach to creating **scalable distributed key/value stores**.

## 🌟 Key Features

1. **🌀 Chord Protocol**  
   - Circular key distribution and Finger Table routing.

2. **🔗 Chain Replication**  
   - Data is replicated, using **Chain Replication**, across multiple nodes for increased redundancy, and availability.
   - _Configurable_ replication factor and _Configurable_ consistency guarantees (LINEARIZABLE or EVENTUAL)

3. **🔒 Dynamic Membership Changes**
   - Add or remove nodes dynamically. 
   - A _Distributed Locking Service_ eliminates race conditions during membership changes (joins/departs).

4. **🐳 Docker-Compose Deployment**  
   - A single command to build and launch the entire environment.

5. **⚡️ Streamlined Administration**  
   - **React + Material-UI** Web Dashboard
   - Interactive **CLI**
   - **REST API** endpoints

## 🔧 How It Works

1. **Bootstrap Node**: Start the ring with a single node that initially spans the entire key range.  
2. **Joining**: Additional nodes contact the ring, triggering graceful key redistribution.  
3. **Departing**: A node transfers its keys to the appropriate node, preserving the ring’s continuity.
4. **Replication**: Writes propagate through a replication chain, ensuring data durability.
The system ensures the replication factor is kept constant after joins and departs.
5. **Queries/Modifications**: Requests are forwarded through finger tables until the responsible node is located. Then the request is propagated along the replication chain.

## 🏁 Getting Started

### ⚡ Quick Start (Docker Compose)

1. **Build and launch** all services:
   ```bash
   docker compose up --build
   ```
   This spins up:
   - 5 Physical Chord DHT Nodes, each with a **Manager** service. (Each node can host _dynamically_ multiple Logical Nodes)
   - The **Locking** service
   - A **React/Material-UI** frontend
   - An **NGINX** service

2. **Open on your desired web broweser**:

   [https://localhost/](https://localhost/)

   **🔐 User Credentials** (for Docker local deployment only):

   - Username: `testuser`
   - Password: `123456`

### 🎮 CLI & Benchmarks

- **Attach to the CLI** for interactive control:
  ```bash
  docker compose -p chordify attach cli
  ```
- **Run performance benchmarks**:
  ```bash
  docker compose -p chordify attach benchmark
  ```
- **Run consistency benchmarks**:
  ```bash
  docker compose -p chordify attach benchmark_consistency
  ```

## 💻 Using the CLI

The **CLI** accepts commands to coordinate nodes and conduct data operations:

- **`list-physicals`** / **`set-physical <ID>`**  
  Enumerates or selects physical (manager) nodes.
- **`list-logicals`** / **`set-logical <ID>`**  
  Enumerates or selects chord nodes within the chosen manager.
- **`spawn-bootstrap`**  
  Creates a *bootstrap* node if none exists, specifying consistency model and replication factor.
- **`spawn`**  
  Adds a *standard* chord node to the ring.
- **`killall`**  
  Removes all chord nodes under a manager.
- **`insert/delete/query <key>`**  
  Performs data manipulations on the ring.
- **`depart`**  
  Graceful node departure.
- **`overlay`**  
  Displays current ring topology (successors, predecessors, and key ranges).

Use **`exit`** to leave the CLI.

## 🌐 Using the Frontend

For an even **friendlier** experience, our **React + Material-UI** app mirrors all CLI functionality with modern web-based interactions:

- **List & select** physical nodes
- **Spawn** or **depart** bootstrap/standard nodes
- **Insert**, **delete**, and **query** data
- **Overlay** for ring structure visualization

---

**🎉 Thank you for exploring Chord DHT!**

© 2025 Andreas Stamos, Harris Platanos, Spyros Galanopoulos. All rights reserved.
