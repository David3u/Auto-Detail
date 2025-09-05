# Auto Detail

An AI powered CLI for automatically detailing software development projects.

## Features

- **Simple Detailing**: Quickly record notes about your work from the command line.
- **AI-Powered Commit Messages**: Generate well-structured commit messages based on your recorded details.
- **Local Storage**: All details are stored locally in simple YAML files.

## Installation

1.  **Install tool:**
    ```bash
    pip install auto-detail
    ```

2.  **Set up your environment:**
    Create a Google Gemini API key at https://aistudio.google.com/apikey . This is required for using the tool. A free tier is available and will usually suffice.
    ```
    auto-detail set_key GEMINI_API_KEY
    ```

## Usage

All commands are run through the `auto-detail` CLI entrypoint.

### Create a New Detail
The `new` command is your primary tool for writing notes with AI to summarize your changes.
```bash
auto-detail
```

or

```bash
auto-detail new
```

This creates a timestamped YAML file in the `.detail/notes/` directory containing your
notes.

### View Details
To see a list of all recorded details:
```bash
auto-detail list
```

### Set working directory base branch
To set the base branch for diff comparison:
```bash
auto-detail set-branch
```

### View current configuration
To view the current configuration:
```bash
auto-detail config
```

## Dev Env Setup
```bash
poetry install
pre-commit install
```
