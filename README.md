# LMBench

**The universal benchmark for local Large Language Models.**

LMBench is a cross-platform tool designed to provide accurate, comparable, and actionable performance metrics for LLMs running on your own hardware. Whether you are running Ollama on a MacBook Air or LM Studio on a multi-GPU rig, LMBench gives you the hard numbers you need to optimize your workflow.

## Features

*   **Universal Compatibility:** Runs seamlessly on Windows, macOS, and Linux.
*   **Hardware Aware:** Automatically detects and profiles your CPU, GPU, and RAM to provide context for your results.
*   **Agnostic Backend:** Supports **Ollama** and **LM Studio** out of the box.
*   **Actionable Metrics:** Measures what matters—Time To First Token (TTFT), Tokens Per Second (TPS), and Memory Pressure.
*   **Vibes:** A clean, modern CLI experience designed for clarity.

## Installation

```bash
pip install lmbench
```

## Usage

```bash
lmbench run
```

## Contributing

We believe in open standards. If you want to add support for a new backend or metric, please open a PR.