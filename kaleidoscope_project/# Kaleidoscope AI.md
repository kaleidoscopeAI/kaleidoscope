# Kaleidoscope AI

A cutting-edge system that can ingest, analyze, and mimic any software through decompilation, 
specification generation, and reconstruction, powered by open-source LLMs via Ollama.

## Features

- Decompile binaries and obfuscated code
- Create specifications from analyzed code using local LLMs
- Reconstruct software with enhanced capabilities
- Generate new software based on learned patterns
- Support for multiple languages (Python, JavaScript, C/C++)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/kaleidoscope-ai.git
cd kaleidoscope-ai
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Ollama for local LLM support:
   - Visit https://ollama.ai to download and install Ollama
   - Start the Ollama server: `ollama serve`
   - Pull a code-specific model: `ollama pull codellama`

4. Install external tools (as needed):
- radare2: https://github.com/radareorg/radare2
- ghidra: https://ghidra-sre.org/
- retdec: https://github.com/avast/retdec
- js-beautify: `npm install -g js-beautify`

## Usage

### Command Line Interface

Ingest and analyze software:
```bash
python kaleidoscope.py ingest --file path/to/software.exe
```

Generate mimicked software:
```bash
python kaleidoscope.py mimic --spec path/to/spec.md --language python
```

Start web interface:
```bash
python kaleidoscope.py web
```

### Web Interface

Navigate to http://localhost:5000 in your browser after starting the web interface.

## Model Management

Kaleidoscope AI uses Ollama to run models locally. To manage your models:

1. Access the settings page in the web interface
2. Pull new models or select from existing models
3. Adjust generation parameters (temperature, token limits)

## Directory Structure

- `/kaleidoscope_workdir`: Working directory for files
  - `/source`: Original software files
  - `/decompiled`: Decompiled and analyzed files
  - `/specs`: Generated specifications
  - `/reconstructed`: Reconstructed and mimicked software

## Advanced Configuration

Edit `config.json` to customize:
- Default Ollama model
- LLM parameters
- API endpoints
- Processing settings

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

