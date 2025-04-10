# External Tools Setup GuideKaleidoscope AI uses several external tools for binary analysis and code processing. This guide explains how to install these tools on different platforms.## Radare2Radare2 is a powerful reverse engineering framework used for binary analysis.### Linux```bashgit clone https://github.com/radareorg/radare2cd radare2sys/install.sh```### macOS```bashbrew install radare2```### WindowsDownload the installer from: https://github.com/radareorg/radare2/releases## GhidraGhidra is an open-source software reverse engineering tool developed by the NSA.1. Download from: https://ghidra-sre.org/2. Extract the archive3. Add the extracted directory to your PATH### Java RequirementGhidra requires Java 11 or newer. Install OpenJDK:#### Linux```bashsudo apt install openjdk-11-jdk  # Debian/Ubuntusudo dnf install java-11-openjdk  # Fedora```#### macOS```bashbrew install openjdk@11```#### WindowsDownload and install from: https://adoptopenjdk.net/## RetDecRetDec is a retargetable machine-code decompiler based on LLVM.### Linux```bashgit clone https://github.com/avast/retdeccd retdecmkdir build && cd buildcmake .. -DCMAKE_INSTALL_PREFIX=$HOME/retdec-installmake -j$(nproc)make install```Add to PATH:```bashecho 'export PATH=$PATH:$HOME/retdec-install/bin' >> ~/.bashrcsource ~/.bashrc```### macOS```bashbrew install cmake boost openssl capstone yaralib z3git clone https://github.com/avast/retdeccd retdecmkdir build && cd buildcmake .. -DCMAKE_INSTALL_PREFIX=$HOME/retdec-installmake -j$(sysctl -n hw.ncpu)make install```Add to PATH:```bashecho 'export PATH=$PATH:$HOME/retdec-install/bin' >> ~/.zshrcsource ~/.zshrc```### Windows

See detailed instructions: https://github.com/avast/retdec/wiki/Windows-Environment

## js-beautify

JavaScript Beautifier is used to format and prettify JavaScript code.

### All Platforms

```bash
npm install -g js-beautify
```

This requires Node.js and npm. If you don't have them installed:

#### Linux
```bash
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### macOS
```bash
brew install node
```

#### Windows
Download from: https://nodejs.org/

## Additional Tools

### Python Packages

Kaleidoscope AI uses several Python packages that are installed through the requirements.txt file:

```bash
pip install -r requirements.txt
```

### Ollama

For local LLM support:

1. Visit https://ollama.ai to download and install Ollama
2. Start the Ollama server: `ollama serve`
3. Pull a code-specific model: `ollama pull codellama`

## Verification

To verify that all tools are installed correctly:

```bash
# Check Radare2
r2 -v

# Check Ghidra
ghidra_server -v

# Check RetDec
retdec-decompiler --help

# Check js-beautify
js-beautify --version

# Check Ollama
ollama list
```

## Troubleshooting

If you encounter issues with any of these tools:

1. Ensure they are properly installed and added to your PATH
2. Check the official documentation for the specific tool
3. For Kaleidoscope AI specific issues, check the GitHub repository or open an issue
