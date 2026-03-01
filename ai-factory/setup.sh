#!/bin/bash
# AI Development Factory Setup Script
# ローカルLLM並列実行クラスターのセットアップ

set -e

echo "🏭 AI Development Factory Setup"
echo "================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="${HOME}/ai-factory"
CONFIG_DIR="${INSTALL_DIR}/config"
MODELS_DIR="${INSTALL_DIR}/models"
LOGS_DIR="${INSTALL_DIR}/logs"

# Functions
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.9+."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_status "Python version: $PYTHON_VERSION"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_warning "Docker is not installed. Some features will be unavailable."
    else
        print_status "Docker is installed"
    fi
    
    # Check Ollama
    if ! command -v ollama &> /dev/null; then
        print_warning "Ollama is not installed. Please install Ollama for local LLM execution."
        print_status "Visit: https://ollama.com/download"
    else
        print_status "Ollama is installed"
    fi
    
    # Check GPU
    if command -v nvidia-smi &> /dev/null; then
        print_status "NVIDIA GPU detected:"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    else
        print_warning "No NVIDIA GPU detected. Performance will be limited to CPU."
    fi
}

# Create directory structure
setup_directories() {
    print_status "Creating directory structure..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$MODELS_DIR"
    mkdir -p "$LOGS_DIR"
    
    # Subdirectories
    mkdir -p "$CONFIG_DIR"/grafana/dashboards
    mkdir -p "$CONFIG_DIR"/grafana/datasources
    mkdir -p "$CONFIG_DIR"/prometheus
    
    print_status "Directories created at: $INSTALL_DIR"
}

# Install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    
    pip3 install --user -q \
        aiohttp \
        redis \
        pyyaml \
        prometheus-client \
        requests \
        pytest \
        pytest-asyncio
    
    print_status "Python dependencies installed"
}

# Download recommended models
download_models() {
    print_status "Checking Ollama models..."
    
    if ! command -v ollama &> /dev/null; then
        print_warning "Ollama not found. Skipping model download."
        return
    fi
    
    # Fast tier models
    print_status "Downloading fast tier models..."
    ollama pull qwen2.5-coder:7b-q4_K_M || print_warning "Failed to pull qwen2.5-coder:7b"
    ollama pull codellama:7b-code-q4 || print_warning "Failed to pull codellama:7b"
    
    # Balanced tier models
    print_status "Downloading balanced tier models..."
    ollama pull qwen2.5-coder:14b-q5 || print_warning "Failed to pull qwen2.5-coder:14b"
    ollama pull deepseek-coder:16b-q5 || print_warning "Failed to pull deepseek-coder:16b"
    
    # Powerful tier models (optional - require more VRAM)
    read -p "Download powerful tier models (32B+, requires 24GB VRAM)? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Downloading powerful tier models..."
        ollama pull qwen2.5-coder:32b-q4 || print_warning "Failed to pull qwen2.5-coder:32b"
        ollama pull deepseek-coder:33b-q4 || print_warning "Failed to pull deepseek-coder:33b"
    fi
    
    print_status "Model download complete"
}

# Setup co-vibe integration
setup_covibe() {
    print_status "Setting up co-vibe integration..."
    
    COVIBE_DIR="${INSTALL_DIR}/co-vibe"
    
    if [ -d "$COVIBE_DIR" ]; then
        print_status "co-vibe already exists, updating..."
        cd "$COVIBE_DIR" && git pull
    else
        print_status "Cloning co-vibe repository..."
        git clone https://github.com/ochyai/co-vibe.git "$COVIBE_DIR"
    fi
    
    # Create co-vibe config
    cat > "${COVIBE_DIR}/.env" << EOF
# AI Factory Configuration
OLLAMA_HOST=http://localhost:11434
CO_VIBE_STRATEGY=auto
CO_VIBE_PORT=8091
CO_VIBE_DEBUG=0
EOF
    
    print_status "co-vibe setup complete"
}

# Create configuration files
create_configs() {
    print_status "Creating configuration files..."
    
    # Prometheus config
    cat > "$CONFIG_DIR/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'ai-factory-router'
    static_configs:
      - targets: ['router:8090']
    metrics_path: /metrics

  - job_name: 'ollama-workers'
    static_configs:
      - targets: 
        - 'worker-t1-01:11434'
        - 'worker-t2-01:11436'
        - 'worker-t3-01:11439'
EOF

    # Grafana datasource
    cat > "$CONFIG_DIR/grafana/datasources/prometheus.yml" << 'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

    print_status "Configuration files created"
}

# Create systemd services (Linux)
setup_systemd() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_status "Setting up systemd services..."
        
        # Router service
        sudo tee /etc/systemd/system/ai-factory-router.service > /dev/null << EOF
[Unit]
Description=AI Factory LLM Router
After=network.target redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/orchestrator/router.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        print_status "Systemd services created"
        print_status "Enable with: sudo systemctl enable ai-factory-router"
    fi
}

# Create launchd plist (macOS)
setup_launchd() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_status "Setting up launchd service..."
        
        LAUNCHD_DIR="${HOME}/Library/LaunchAgents"
        mkdir -p "$LAUNCHD_DIR"
        
        cat > "$LAUNCHD_DIR/com.loreanchor.ai-factory.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loreanchor.ai-factory</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${INSTALL_DIR}/orchestrator/router.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${INSTALL_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOGS_DIR}/router.log</string>
    <key>StandardErrorPath</key>
    <string>${LOGS_DIR}/router.error.log</string>
</dict>
</plist>
EOF

        print_status "Launchd service created"
        print_status "Load with: launchctl load ${LAUNCHD_DIR}/com.loreanchor.ai-factory.plist"
    fi
}

# Create CLI wrapper
create_cli() {
    print_status "Creating CLI wrapper..."
    
    cat > "$INSTALL_DIR/ai-factory" << 'EOF'
#!/bin/bash
# AI Factory CLI

INSTALL_DIR="${HOME}/ai-factory"
COMMAND=$1

case $COMMAND in
    start)
        echo "🏭 Starting AI Factory..."
        redis-server --daemonize yes
        cd "$INSTALL_DIR" && python3 orchestrator/router.py &
        echo $! > /tmp/ai-factory.pid
        echo "Router started on http://localhost:8090"
        ;;
    stop)
        echo "🛑 Stopping AI Factory..."
        if [ -f /tmp/ai-factory.pid ]; then
            kill $(cat /tmp/ai-factory.pid)
            rm /tmp/ai-factory.pid
        fi
        redis-cli shutdown
        ;;
    status)
        echo "📊 AI Factory Status"
        if [ -f /tmp/ai-factory.pid ]; then
            echo "Router: Running (PID: $(cat /tmp/ai-factory.pid))"
        else
            echo "Router: Stopped"
        fi
        redis-cli ping 2>/dev/null && echo "Redis: Running" || echo "Redis: Stopped"
        ;;
    submit)
        shift
        curl -X POST http://localhost:8090/api/v1/submit \
            -H "Content-Type: application/json" \
            -d "$@"
        ;;
    models)
        echo "📦 Available Models"
        ollama list 2>/dev/null || echo "Ollama not running"
        ;;
    dashboard)
        open http://localhost:3000 2>/dev/null || echo "Grafana: http://localhost:3000"
        ;;
    *)
        echo "AI Factory CLI"
        echo ""
        echo "Usage: ai-factory <command>"
        echo ""
        echo "Commands:"
        echo "  start       Start the AI Factory"
        echo "  stop        Stop the AI Factory"
        echo "  status      Check status"
        echo "  submit      Submit a task"
        echo "  models      List available models"
        echo "  dashboard   Open Grafana dashboard"
        ;;
esac
EOF

    chmod +x "$INSTALL_DIR/ai-factory"
    
    # Add to PATH if not already
    if [[ ":$PATH:" != *":${INSTALL_DIR}:"* ]]; then
        echo "export PATH=\"\$PATH:${INSTALL_DIR}\"" >> ~/.bashrc
        echo "export PATH=\"\$PATH:${INSTALL_DIR}\"" >> ~/.zshrc 2>/dev/null || true
        print_status "Added to PATH. Please restart your shell or run:"
        print_status "  export PATH=\"\$PATH:${INSTALL_DIR}\""
    fi
}

# Print summary
print_summary() {
    echo ""
    echo "================================"
    echo -e "${GREEN}✅ Setup Complete!${NC}"
    echo "================================"
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo ""
    echo "Next steps:"
    echo "  1. Start services: ai-factory start"
    echo "  2. Check status:   ai-factory status"
    echo "  3. Submit task:    ai-factory submit '{\"description\": \"Create React component\", \"prompt\": \"...\"}'"
    echo "  4. View dashboard: ai-factory dashboard"
    echo ""
    echo "Documentation: $INSTALL_DIR/docs/"
    echo "Logs: $LOGS_DIR/"
    echo ""
    echo "For Docker deployment:"
    echo "  cd $INSTALL_DIR && docker-compose up -d"
}

# Main
main() {
    check_requirements
    setup_directories
    install_python_deps
    
    # Copy files to install directory
    cp -r . "$INSTALL_DIR/"
    
    download_models
    setup_covibe
    create_configs
    create_cli
    
    # Setup service managers
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        setup_systemd
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        setup_launchd
    fi
    
    print_summary
}

# Run
main "$@"
