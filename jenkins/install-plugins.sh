#!/bin/bash
# ============================================================
# Jenkins Post-Install Plugin Setup Script
# Run once after Jenkins first boots:
#   bash jenkins/install-plugins.sh
# ============================================================

JENKINS_URL="http://localhost:8080"
JENKINS_USER="admin"
# Get password from: docker exec unisora-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
JENKINS_PASS="${1:-admin}"

echo "Installing required Jenkins plugins..."

PLUGINS=(
  "git"
  "github"
  "github-branch-source"
  "workflow-aggregator"          # Pipeline
  "pipeline-stage-view"
  "blueocean"                    # Modern pipeline UI
  "docker-workflow"
  "kubernetes"                   # Jenkins on K8s agent support
  "kubernetes-cli"               # kubectl in pipeline steps
  "credentials-binding"
  "ssh-agent"
  "slack"                        # Slack notifications (optional)
  "build-timeout"
  "timestamper"
  "ws-cleanup"
)

for plugin in "${PLUGINS[@]}"; do
  echo "  Installing: $plugin"
  curl -s -X POST \
    "${JENKINS_URL}/pluginManager/installNecessaryPlugins" \
    -u "${JENKINS_USER}:${JENKINS_PASS}" \
    -d "<jenkins><install plugin='${plugin}@latest'/></jenkins>" \
    -H "Content-Type: text/xml" > /dev/null
done

echo "✅ Plugins installed. Restart Jenkins: docker restart unisora-jenkins"
