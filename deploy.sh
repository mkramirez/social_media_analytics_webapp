#!/bin/bash

# Social Media Analytics Platform - Deployment Script
# This script automates the deployment process to AWS ECS

set -e

# Configuration
ENVIRONMENT=${ENVIRONMENT:-production}
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-""}
ECR_BACKEND_REPO="social-analytics/backend"
ECR_FRONTEND_REPO="social-analytics/frontend"
ECS_CLUSTER="social-analytics-cluster"
ECS_SERVICE="backend-service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    echo_info "Checking prerequisites..."

    if ! command -v aws &> /dev/null; then
        echo_error "AWS CLI not found. Please install it first."
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        echo_error "Docker not found. Please install it first."
        exit 1
    fi

    if [ -z "$AWS_ACCOUNT_ID" ]; then
        echo_error "AWS_ACCOUNT_ID not set. Please set it in the script or as an environment variable."
        exit 1
    fi

    echo_info "Prerequisites check passed ✓"
}

# Build Docker images
build_images() {
    echo_info "Building Docker images..."

    # Build backend
    echo_info "Building backend image..."
    docker build -t ${ECR_BACKEND_REPO}:latest ./backend
    docker tag ${ECR_BACKEND_REPO}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_BACKEND_REPO}:latest
    docker tag ${ECR_BACKEND_REPO}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_BACKEND_REPO}:${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)

    # Build frontend
    echo_info "Building frontend image..."
    docker build -t ${ECR_FRONTEND_REPO}:latest ./frontend
    docker tag ${ECR_FRONTEND_REPO}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_FRONTEND_REPO}:latest
    docker tag ${ECR_FRONTEND_REPO}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_FRONTEND_REPO}:${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)

    echo_info "Docker images built successfully ✓"
}

# Login to ECR
ecr_login() {
    echo_info "Logging in to ECR..."
    aws ecr get-login-password --region ${AWS_REGION} | \
        docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
    echo_info "ECR login successful ✓"
}

# Push images to ECR
push_images() {
    echo_info "Pushing images to ECR..."

    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_BACKEND_REPO}:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_BACKEND_REPO}:${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S) || true

    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_FRONTEND_REPO}:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_FRONTEND_REPO}:${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S) || true

    echo_info "Images pushed successfully ✓"
}

# Update ECS service
update_service() {
    echo_info "Updating ECS service..."

    # Force new deployment
    aws ecs update-service \
        --cluster ${ECS_CLUSTER} \
        --service ${ECS_SERVICE} \
        --force-new-deployment \
        --region ${AWS_REGION}

    echo_info "Service update initiated ✓"
}

# Wait for deployment to complete
wait_for_deployment() {
    echo_info "Waiting for deployment to complete..."

    aws ecs wait services-stable \
        --cluster ${ECS_CLUSTER} \
        --services ${ECS_SERVICE} \
        --region ${AWS_REGION}

    echo_info "Deployment completed successfully ✓"
}

# Run database migrations
run_migrations() {
    echo_info "Running database migrations..."
    echo_warn "Migration step not automated. Please run migrations manually if needed."
    # Uncomment and modify if you have a migration task
    # aws ecs run-task \
    #     --cluster ${ECS_CLUSTER} \
    #     --task-definition migration-task \
    #     --launch-type FARGATE
}

# Main deployment function
deploy() {
    echo_info "Starting deployment to ${ENVIRONMENT} environment..."

    check_prerequisites
    build_images
    ecr_login
    push_images
    update_service
    wait_for_deployment

    echo_info "✅ Deployment completed successfully!"
    echo_info "Check the service status:"
    echo_info "  aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} --region ${AWS_REGION}"
}

# Rollback function
rollback() {
    echo_warn "Rolling back to previous task definition..."

    # Get current task definition
    CURRENT_TASK_DEF=$(aws ecs describe-services \
        --cluster ${ECS_CLUSTER} \
        --services ${ECS_SERVICE} \
        --region ${AWS_REGION} \
        --query 'services[0].taskDefinition' \
        --output text)

    echo_info "Current task definition: ${CURRENT_TASK_DEF}"

    # Extract revision number
    CURRENT_REVISION=$(echo ${CURRENT_TASK_DEF} | grep -oP ':\K\d+$')
    PREVIOUS_REVISION=$((CURRENT_REVISION - 1))

    if [ $PREVIOUS_REVISION -lt 1 ]; then
        echo_error "Cannot rollback: No previous revision available"
        exit 1
    fi

    TASK_DEF_FAMILY=$(echo ${CURRENT_TASK_DEF} | grep -oP '.*/\K[^:]+')
    PREVIOUS_TASK_DEF="${TASK_DEF_FAMILY}:${PREVIOUS_REVISION}"

    echo_info "Rolling back to: ${PREVIOUS_TASK_DEF}"

    aws ecs update-service \
        --cluster ${ECS_CLUSTER} \
        --service ${ECS_SERVICE} \
        --task-definition ${PREVIOUS_TASK_DEF} \
        --force-new-deployment \
        --region ${AWS_REGION}

    echo_info "Rollback initiated ✓"
    wait_for_deployment
    echo_info "✅ Rollback completed successfully!"
}

# Show usage
usage() {
    echo "Usage: $0 {deploy|rollback|build|push}"
    echo ""
    echo "Commands:"
    echo "  deploy    - Full deployment (build, push, update)"
    echo "  rollback  - Rollback to previous task definition"
    echo "  build     - Build Docker images only"
    echo "  push      - Push images to ECR only"
    echo ""
    echo "Environment Variables:"
    echo "  ENVIRONMENT       - Deployment environment (default: production)"
    echo "  AWS_REGION        - AWS region (default: us-east-1)"
    echo "  AWS_ACCOUNT_ID    - AWS account ID (required)"
    exit 1
}

# Main script logic
case "${1:-}" in
    deploy)
        deploy
        ;;
    rollback)
        rollback
        ;;
    build)
        check_prerequisites
        build_images
        ;;
    push)
        check_prerequisites
        ecr_login
        push_images
        ;;
    *)
        usage
        ;;
esac
