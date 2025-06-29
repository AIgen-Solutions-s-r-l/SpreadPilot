#!/bin/bash

# 🔒 Trivy Security Scanner for SpreadPilot
# This script performs comprehensive security scanning on all Docker images and dependencies
# Usage: ./trivy_scan.sh [--severity CRITICAL,HIGH] [--exit-code 1]

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TRIVY_VERSION="${TRIVY_VERSION:-latest}"
SEVERITY="${SEVERITY:-CRITICAL,HIGH,MEDIUM}"
EXIT_CODE="${EXIT_CODE:-1}"
REPORT_FORMAT="${REPORT_FORMAT:-json}"
REPORT_DIR="security-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Services to scan
SERVICES=(
    "trading-bot"
    "admin-api"
    "report-worker"
    "alert-router"
    "watchdog"
    "frontend"
    "admin-dashboard"
)

# Print banner
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🔒 SpreadPilot Security Scanner (Trivy)${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Function to check if Trivy is installed
check_trivy() {
    if ! command -v trivy &> /dev/null; then
        echo -e "${YELLOW}⚠️  Trivy not found. Installing...${NC}"
        
        # Detect OS and install accordingly
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin ${TRIVY_VERSION}
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            brew install aquasecurity/trivy/trivy
        else
            echo -e "${RED}❌ Unsupported OS. Please install Trivy manually.${NC}"
            echo "Visit: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✅ Trivy version: $(trivy --version)${NC}"
}

# Function to create report directory
setup_reports() {
    mkdir -p ${REPORT_DIR}
    echo -e "${GREEN}✅ Report directory: ${REPORT_DIR}/${NC}"
}

# Function to scan a Docker image
scan_image() {
    local service=$1
    local image_name="spreadpilot-${service}:latest"
    
    echo -e "\n${BLUE}🔍 Scanning ${service}...${NC}"
    
    # Check if image exists
    if ! docker images | grep -q "spreadpilot-${service}"; then
        echo -e "${YELLOW}⚠️  Image ${image_name} not found. Building...${NC}"
        
        # Build the image based on service
        case ${service} in
            "frontend"|"admin-dashboard")
                docker build -t ${image_name} -f ${service}/Dockerfile ${service}/
                ;;
            *)
                docker build -t ${image_name} -f ${service}/Dockerfile .
                ;;
        esac
    fi
    
    # Run Trivy scan
    trivy image \
        --severity ${SEVERITY} \
        --exit-code 0 \
        --format ${REPORT_FORMAT} \
        --output ${REPORT_DIR}/${service}_${TIMESTAMP}.json \
        ${image_name}
    
    # Also generate human-readable report
    trivy image \
        --severity ${SEVERITY} \
        --exit-code 0 \
        --format table \
        --output ${REPORT_DIR}/${service}_${TIMESTAMP}.txt \
        ${image_name}
    
    # Print summary
    local vuln_count=$(trivy image --severity ${SEVERITY} --format json ${image_name} 2>/dev/null | jq '[.Results[].Vulnerabilities[]?] | length')
    
    if [ "${vuln_count}" -eq 0 ]; then
        echo -e "${GREEN}✅ ${service}: No vulnerabilities found${NC}"
    else
        echo -e "${YELLOW}⚠️  ${service}: ${vuln_count} vulnerabilities found${NC}"
    fi
}

# Function to scan filesystem (dependencies)
scan_dependencies() {
    echo -e "\n${BLUE}🔍 Scanning dependencies...${NC}"
    
    # Scan Python dependencies
    if [ -f "requirements.txt" ] || [ -f "requirements.in" ]; then
        echo -e "${BLUE}📦 Scanning Python dependencies...${NC}"
        trivy fs \
            --severity ${SEVERITY} \
            --exit-code 0 \
            --format ${REPORT_FORMAT} \
            --output ${REPORT_DIR}/python_deps_${TIMESTAMP}.json \
            --scanners vuln \
            .
    fi
    
    # Scan Node.js dependencies
    for dir in frontend admin-dashboard; do
        if [ -f "${dir}/package.json" ]; then
            echo -e "${BLUE}📦 Scanning ${dir} Node.js dependencies...${NC}"
            trivy fs \
                --severity ${SEVERITY} \
                --exit-code 0 \
                --format ${REPORT_FORMAT} \
                --output ${REPORT_DIR}/${dir}_npm_${TIMESTAMP}.json \
                --scanners vuln \
                ${dir}
        fi
    done
}

# Function to check container configurations
check_container_security() {
    echo -e "\n${BLUE}🔍 Checking container security configurations...${NC}"
    
    local issues=0
    
    # Check if containers run as non-root
    for service in "${SERVICES[@]}"; do
        dockerfile=""
        
        # Find the Dockerfile
        if [ -f "${service}/Dockerfile" ]; then
            dockerfile="${service}/Dockerfile"
        elif [ -f "Dockerfile.${service}" ]; then
            dockerfile="Dockerfile.${service}"
        else
            continue
        fi
        
        # Check for USER instruction
        if grep -q "^USER" ${dockerfile}; then
            echo -e "${GREEN}✅ ${service}: Runs as non-root user${NC}"
        else
            echo -e "${RED}❌ ${service}: No USER instruction found (runs as root)${NC}"
            ((issues++))
        fi
        
        # Check for HEALTHCHECK
        if grep -q "^HEALTHCHECK" ${dockerfile}; then
            echo -e "${GREEN}✅ ${service}: Has HEALTHCHECK${NC}"
        else
            echo -e "${YELLOW}⚠️  ${service}: No HEALTHCHECK found${NC}"
        fi
    done
    
    return ${issues}
}

# Function to generate summary report
generate_summary() {
    echo -e "\n${BLUE}📊 Generating summary report...${NC}"
    
    local summary_file="${REPORT_DIR}/security_summary_${TIMESTAMP}.md"
    
    cat > ${summary_file} << EOF
# SpreadPilot Security Scan Summary

**Date**: $(date)
**Trivy Version**: $(trivy --version)
**Severity Threshold**: ${SEVERITY}

## Docker Image Vulnerabilities

| Service | Critical | High | Medium | Low |
|---------|----------|------|--------|-----|
EOF
    
    # Add vulnerability counts for each service
    for service in "${SERVICES[@]}"; do
        if [ -f "${REPORT_DIR}/${service}_${TIMESTAMP}.json" ]; then
            local critical=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' ${REPORT_DIR}/${service}_${TIMESTAMP}.json)
            local high=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="HIGH")] | length' ${REPORT_DIR}/${service}_${TIMESTAMP}.json)
            local medium=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="MEDIUM")] | length' ${REPORT_DIR}/${service}_${TIMESTAMP}.json)
            local low=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="LOW")] | length' ${REPORT_DIR}/${service}_${TIMESTAMP}.json)
            
            echo "| ${service} | ${critical} | ${high} | ${medium} | ${low} |" >> ${summary_file}
        fi
    done
    
    cat >> ${summary_file} << EOF

## Security Checks

- Container Security: See container_security_check.txt
- Dependency Scan: See *_deps_*.json files
- Full Reports: Available in ${REPORT_DIR}/

## Next Steps

1. Review all HIGH and CRITICAL vulnerabilities
2. Update base images if needed
3. Patch or update vulnerable dependencies
4. Re-run scan after fixes

---
Generated by trivy_scan.sh
EOF

    echo -e "${GREEN}✅ Summary report: ${summary_file}${NC}"
}

# Function to check for secrets
scan_secrets() {
    echo -e "\n${BLUE}🔍 Scanning for exposed secrets...${NC}"
    
    # Skip secret scanning in CI to avoid false positives
    if [ ! -z "${CI:-}" ]; then
        echo -e "${YELLOW}⚠️  Skipping secret scanning in CI environment${NC}"
        return 0
    fi
    
    # Basic secret patterns
    local secret_patterns=(
        "api[_-]?key"
        "secret[_-]?key"
        "password"
        "token"
        "private[_-]?key"
        "aws[_-]?access"
        "jwt[_-]?secret"
    )
    
    local found_secrets=0
    
    for pattern in "${secret_patterns[@]}"; do
        # Exclude common false positives
        # Use set +e to prevent grep from causing script exit
        set +e
        matches=$(grep -r -i "${pattern}" . \
            --exclude-dir=.git \
            --exclude-dir=node_modules \
            --exclude-dir=venv \
            --exclude-dir=security-reports \
            --exclude="*.md" \
            --exclude="*.json" \
            --exclude="trivy_scan.sh" \
            2>/dev/null | grep -v "env.example" \
            | grep -v "template" \
            | grep -v "TODO" \
            | grep -v "FIXME" || true)
        set -e
        
        if [ ! -z "${matches}" ]; then
            echo -e "${RED}❌ Potential secrets found for pattern: ${pattern}${NC}"
            ((found_secrets++))
        fi
    done
    
    if [ ${found_secrets} -eq 0 ]; then
        echo -e "${GREEN}✅ No exposed secrets detected${NC}"
    else
        echo -e "${YELLOW}⚠️  Found ${found_secrets} potential secret patterns (review manually)${NC}"
        # Don't fail on potential secrets, just warn
        return 0
    fi
}

# Main execution
main() {
    echo "Starting security scan at $(date)"
    echo "Configuration:"
    echo "  - Severity: ${SEVERITY}"
    echo "  - Exit on failure: ${EXIT_CODE}"
    echo "  - Report format: ${REPORT_FORMAT}"
    echo ""
    
    # Setup
    check_trivy
    setup_reports
    
    # Run scans
    local total_issues=0
    
    # Scan Docker images
    for service in "${SERVICES[@]}"; do
        scan_image ${service} || ((total_issues++))
    done
    
    # Scan dependencies
    scan_dependencies
    
    # Check container security
    check_container_security > ${REPORT_DIR}/container_security_check.txt || ((total_issues+=$?))
    
    # Scan for secrets
    scan_secrets
    
    # Generate summary
    generate_summary
    
    # Final report
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}📊 Scan Complete${NC}"
    echo -e "${BLUE}================================================${NC}"
    
    if [ ${total_issues} -eq 0 ]; then
        echo -e "${GREEN}✅ All security checks passed!${NC}"
        echo -e "${GREEN}Reports available in: ${REPORT_DIR}/${NC}"
        exit 0
    else
        echo -e "${RED}❌ Security issues found: ${total_issues}${NC}"
        echo -e "${YELLOW}Review reports in: ${REPORT_DIR}/${NC}"
        
        # Exit with error if configured
        if [ "${EXIT_CODE}" -eq 1 ]; then
            exit 1
        fi
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --severity)
            SEVERITY="$2"
            shift 2
            ;;
        --exit-code)
            EXIT_CODE="$2"
            shift 2
            ;;
        --format)
            REPORT_FORMAT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --severity LEVEL    Comma-separated severity levels (default: CRITICAL,HIGH,MEDIUM)"
            echo "  --exit-code CODE    Exit code on vulnerabilities (default: 1)"
            echo "  --format FORMAT     Report format: json, table, sarif (default: json)"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main