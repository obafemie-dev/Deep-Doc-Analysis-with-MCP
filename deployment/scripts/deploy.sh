#!/bin/bash

# ============================================================================
# Deep-Doc-Analysis Production Deployment Script
# ============================================================================
#
# PURPOSE:
#   Automated deployment of Deep-Doc-Analysis to Hetzner server
#
# USAGE:
#   ./deploy.sh --init          # First-time setup
#   ./deploy.sh --update        # Update existing deployment
#   ./deploy.sh --restart       # Restart all services
#   ./deploy.sh --rollback      # Rollback to previous version
#
# REQUIREMENTS:
#   - Ubuntu 22.04 LTS on Hetzner CX31+ server
#   - Root or sudo access
#   - Git installed
#   - Internet connection
#
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# ============================================================================
# Configuration
# ============================================================================

# Application directory
APP_DIR="/opt/deepdoc"
REPO_URL="https://github.com/YOUR_USERNAME/Deep-Doc-Analysis-with-MCP.git"

# Directories
DATA_DIR="$APP_DIR/data"
UPLOADS_DIR="$APP_DIR/uploads"
LOGS_DIR="$APP_DIR/logs"
BACKUPS_DIR="$APP_DIR/backups"
SCRIPTS_DIR="$APP_DIR/scripts"

# Docker Compose file
COMPOSE_FILE="docker-compose.prod.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# Functions
# ============================================================================

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
    exit 1
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Please run as root or with sudo"
    fi
}

check_dependencies() {
    log "Checking system dependencies..."

    # Check for required commands
    local deps=("docker" "docker-compose" "git" "nginx" "certbot")

    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error "$cmd is not installed. Please install it first."
        fi
    done

    log "All dependencies are installed"
}

install_docker() {
    log "Installing Docker..."

    # Update package index
    apt-get update

    # Install prerequisites
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Set up Docker repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
        https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    # Verify installation
    docker --version || error "Docker installation failed"

    log "Docker installed successfully"
}

install_nginx() {
    log "Installing Nginx..."

    apt-get update
    apt-get install -y nginx

    # Start and enable Nginx
    systemctl start nginx
    systemctl enable nginx

    log "Nginx installed successfully"
}

install_certbot() {
    log "Installing Certbot..."

    apt-get update
    apt-get install -y certbot python3-certbot-nginx

    log "Certbot installed successfully"
}

setup_firewall() {
    log "Configuring firewall..."

    # Install UFW if not present
    apt-get install -y ufw

    # Default policies
    ufw default deny incoming
    ufw default allow outgoing

    # Allow SSH (be careful!)
    ufw allow 22/tcp

    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp

    # Enable firewall
    echo "y" | ufw enable

    ufw status

    log "Firewall configured"
}

setup_fail2ban() {
    log "Installing and configuring fail2ban..."

    apt-get install -y fail2ban

    # Create jail configuration
    cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port    = 22
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
port    = http,https
logpath = /var/log/nginx/error.log
EOF

    # Start and enable fail2ban
    systemctl start fail2ban
    systemctl enable fail2ban

    log "fail2ban configured"
}

create_directories() {
    log "Creating application directories..."

    # Create main directories
    mkdir -p "$APP_DIR"
    mkdir -p "$DATA_DIR"/{analytics,metabase}
    mkdir -p "$UPLOADS_DIR"
    mkdir -p "$LOGS_DIR"
    mkdir -p "$BACKUPS_DIR"/{analytics,uploads,metabase,config}
    mkdir -p "$SCRIPTS_DIR"

    # Set permissions
    chmod 755 "$APP_DIR"
    chmod 755 "$UPLOADS_DIR"
    chmod 750 "$DATA_DIR"
    chmod 750 "$BACKUPS_DIR"

    log "Directories created"
}

clone_repository() {
    log "Cloning application repository..."

    if [ -d "$APP_DIR/app" ]; then
        warn "Application directory already exists, skipping clone"
    else
        git clone "$REPO_URL" "$APP_DIR/app" || \
            error "Failed to clone repository"

        log "Repository cloned successfully"
    fi
}

setup_environment() {
    log "Setting up environment configuration..."

    if [ ! -f "$APP_DIR/.env.production" ]; then
        warn ".env.production not found!"
        echo ""
        echo "Please create $APP_DIR/.env.production from the template:"
        echo "  1. Copy .env.production.template to $APP_DIR/.env.production"
        echo "  2. Fill in all required values (API keys, domain, etc.)"
        echo "  3. Run this script again"
        echo ""
        error "Environment file missing"
    fi

    # Set correct permissions
    chmod 600 "$APP_DIR/.env.production"

    # Copy to app directory
    cp "$APP_DIR/.env.production" "$APP_DIR/app/.env.production"

    log "Environment configured"
}

setup_nginx() {
    log "Setting up Nginx reverse proxy..."

    # Copy Nginx configuration
    if [ -f "$APP_DIR/app/deployment/nginx/deepdoc.conf" ]; then
        cp "$APP_DIR/app/deployment/nginx/deepdoc.conf" \
            /etc/nginx/sites-available/deepdoc

        # Prompt for domain name
        read -p "Enter your domain name (e.g., example.com): " DOMAIN_NAME

        # Replace placeholder with actual domain
        sed -i "s/yourdomain.com/$DOMAIN_NAME/g" /etc/nginx/sites-available/deepdoc

        # Enable site
        ln -sf /etc/nginx/sites-available/deepdoc /etc/nginx/sites-enabled/

        # Remove default site
        rm -f /etc/nginx/sites-enabled/default

        # Test configuration
        nginx -t || error "Nginx configuration test failed"

        # Reload Nginx
        systemctl reload nginx

        log "Nginx configured for domain: $DOMAIN_NAME"
    else
        warn "Nginx configuration not found, skipping..."
    fi
}

setup_ssl() {
    log "Setting up SSL certificate..."

    read -p "Enter your domain name (e.g., example.com): " DOMAIN_NAME
    read -p "Enter your email for SSL notifications: " EMAIL

    # Obtain SSL certificate
    certbot --nginx \
        -d "$DOMAIN_NAME" \
        -d "www.$DOMAIN_NAME" \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" || warn "SSL certificate setup failed (manual setup may be required)"

    # Test auto-renewal
    certbot renew --dry-run || warn "SSL auto-renewal test failed"

    log "SSL certificate configured"
}

build_and_start() {
    log "Building and starting Docker containers..."

    cd "$APP_DIR/app"

    # Pull latest changes (if updating)
    if [ "${UPDATE_MODE:-false}" = true ]; then
        git pull origin main || warn "Git pull failed"
    fi

    # Build images
    docker-compose -f "$COMPOSE_FILE" --env-file .env.production build

    # Start services
    docker-compose -f "$COMPOSE_FILE" --env-file .env.production up -d

    # Wait for services to start
    sleep 10

    # Check service status
    docker-compose -f "$COMPOSE_FILE" ps

    log "Docker containers started"
}

setup_backup_cron() {
    log "Setting up automated backups..."

    # Copy backup script
    if [ -f "$APP_DIR/app/deployment/scripts/backup.sh" ]; then
        cp "$APP_DIR/app/deployment/scripts/backup.sh" "$SCRIPTS_DIR/"
        chmod +x "$SCRIPTS_DIR/backup.sh"

        # Add to crontab
        CRON_JOB="0 2 * * * $SCRIPTS_DIR/backup.sh >> /var/log/deepdoc-backup.log 2>&1"

        # Check if cron job already exists
        if ! crontab -l 2>/dev/null | grep -q "$SCRIPTS_DIR/backup.sh"; then
            (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
            log "Backup cron job added (daily at 2 AM)"
        else
            log "Backup cron job already exists"
        fi
    else
        warn "Backup script not found, skipping automation"
    fi
}

verify_deployment() {
    log "Verifying deployment..."

    # Check if containers are running
    local running=$(docker-compose -f "$APP_DIR/app/$COMPOSE_FILE" ps -q | wc -l)

    if [ "$running" -eq 0 ]; then
        error "No containers are running"
    fi

    # Check backend health
    sleep 5
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "✓ Backend is healthy"
    else
        warn "✗ Backend health check failed"
    fi

    # Check frontend
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log "✓ Frontend is accessible"
    else
        warn "✗ Frontend is not accessible"
    fi

    log "Deployment verification complete"
}

print_next_steps() {
    echo ""
    echo "=========================================="
    echo "Deployment Complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Access Metabase via SSH tunnel:"
    echo "   ssh -L 3001:localhost:3001 root@$(hostname -I | awk '{print $1}')"
    echo "   Then open: http://localhost:3001"
    echo ""
    echo "2. Monitor logs:"
    echo "   docker-compose -f $APP_DIR/app/$COMPOSE_FILE logs -f"
    echo ""
    echo "3. Test your application:"
    echo "   Visit: https://$(grep server_name /etc/nginx/sites-available/deepdoc | head -1 | awk '{print $2}' | tr -d ';')"
    echo ""
    echo "4. Set up monitoring (recommended):"
    echo "   - UptimeRobot: https://uptimerobot.com"
    echo "   - Sentry: https://sentry.io"
    echo ""
    echo "=========================================="
}

# ============================================================================
# Main Execution
# ============================================================================

init_deployment() {
    log "Starting initial deployment..."

    check_root

    # System setup
    log "=== Phase 1: System Setup ==="
    install_docker
    install_nginx
    install_certbot
    setup_firewall
    setup_fail2ban

    # Application setup
    log "=== Phase 2: Application Setup ==="
    create_directories
    clone_repository
    setup_environment

    # Web server setup
    log "=== Phase 3: Web Server Setup ==="
    setup_nginx
    setup_ssl

    # Deploy application
    log "=== Phase 4: Application Deployment ==="
    build_and_start

    # Post-deployment
    log "=== Phase 5: Post-Deployment ==="
    setup_backup_cron
    verify_deployment

    print_next_steps
}

update_deployment() {
    log "Updating deployment..."

    check_root
    check_dependencies

    cd "$APP_DIR/app"

    # Pull latest changes
    git pull origin main

    # Rebuild and restart
    UPDATE_MODE=true build_and_start

    verify_deployment

    log "Update complete"
}

restart_services() {
    log "Restarting services..."

    cd "$APP_DIR/app"

    docker-compose -f "$COMPOSE_FILE" restart

    verify_deployment

    log "Services restarted"
}

rollback_deployment() {
    log "Rolling back to previous version..."

    cd "$APP_DIR/app"

    # Get last commit hash
    git log --oneline -n 2

    read -p "Enter commit hash to rollback to: " COMMIT_HASH

    git checkout "$COMMIT_HASH"

    build_and_start

    verify_deployment

    log "Rollback complete"
}

# ============================================================================
# Command Line Interface
# ============================================================================

show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --init      First-time deployment setup"
    echo "  --update    Update existing deployment"
    echo "  --restart   Restart all services"
    echo "  --rollback  Rollback to previous version"
    echo "  --help      Show this help message"
    echo ""
}

# Parse command line arguments
case "${1:-}" in
    --init)
        init_deployment
        ;;
    --update)
        update_deployment
        ;;
    --restart)
        restart_services
        ;;
    --rollback)
        rollback_deployment
        ;;
    --help)
        show_usage
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
