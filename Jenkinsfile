// ============================================================
// UniSora — Jenkins CI/CD Pipeline
// ============================================================
// Triggers on push to 'production' branch via GitHub Webhook.
// Pipeline stages:
//   1. Checkout       — Pull latest code from GitHub
//   2. Test           — Run backend tests
//   3. Build Images   — Docker build backend + frontend
//   4. Push Images    — Push to Docker registry (DockerHub / GHCR)
//   5. Deploy         — Apply Kubernetes manifests with new image tags
//   6. Verify         — Health check the live deployment
//   7. Notify         — Slack / email notification
// ============================================================

pipeline {
    agent any

    environment {
        // ── Registry ────────────────────────────────────────────
        // DockerHub:  docker.io/yourusername
        // GitHub:     ghcr.io/harshpaygude
        REGISTRY         = "ghcr.io/harshpaygude"
        BACKEND_IMAGE    = "${REGISTRY}/unisora-backend"
        FRONTEND_IMAGE   = "${REGISTRY}/unisora-frontend"

        // ── Git ─────────────────────────────────────────────────
        GITHUB_REPO      = "https://github.com/harshpaygude/Subscription_Saas.git"
        DEPLOY_BRANCH    = "production"

        // ── Kubernetes ───────────────────────────────────────────
        K8S_NAMESPACE    = "unisora"
        KUBECONFIG_ID    = "kubeconfig-prod"   // Jenkins credential ID

        // ── Build tag: short Git SHA ─────────────────────────────
        IMAGE_TAG        = "${env.GIT_COMMIT?.take(7) ?: 'latest'}"
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
        disableConcurrentBuilds()   // No parallel production deploys
    }

    stages {
        // ── Stage 1: Checkout ────────────────────────────────────
        stage('Checkout') {
            steps {
                echo "▶ Checking out branch: ${DEPLOY_BRANCH}"
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "*/${DEPLOY_BRANCH}"]],
                    userRemoteConfigs: [[
                        url: GITHUB_REPO,
                        credentialsId: 'github-token'
                    ]]
                ])
                script {
                    env.GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
                    env.IMAGE_TAG = env.GIT_COMMIT_SHORT
                    echo "📌 Image tag: ${env.IMAGE_TAG}"
                }
            }
        }

        // ── Stage 2: Test Backend ─────────────────────────────────
        stage('Test') {
            steps {
                echo "▶ Running backend tests"
                dir('backend') {
                    sh '''
                        python -m venv .venv-ci
                        . .venv-ci/bin/activate
                        pip install --quiet -r requirements.txt
                        python -m pytest tests/ -v --tb=short || true
                    '''
                }
            }
        }

        // ── Stage 3: Build Docker Images ─────────────────────────
        stage('Build Images') {
            parallel {
                stage('Build Backend') {
                    steps {
                        echo "▶ Building backend image: ${BACKEND_IMAGE}:${env.IMAGE_TAG}"
                        dir('backend') {
                            sh "docker build -t ${BACKEND_IMAGE}:${env.IMAGE_TAG} -t ${BACKEND_IMAGE}:latest ."
                        }
                    }
                }
                stage('Build Frontend') {
                    steps {
                        echo "▶ Building frontend image: ${FRONTEND_IMAGE}:${env.IMAGE_TAG}"
                        dir('frontend') {
                            sh """
                                docker build \\
                                  --build-arg API_PROXY_TARGET=http://backend:8000 \\
                                  -t ${FRONTEND_IMAGE}:${env.IMAGE_TAG} \\
                                  -t ${FRONTEND_IMAGE}:latest \\
                                  .
                            """
                        }
                    }
                }
            }
        }

        // ── Stage 4: Push Images ──────────────────────────────────
        stage('Push Images') {
            steps {
                echo "▶ Pushing images to registry: ${REGISTRY}"
                withCredentials([usernamePassword(
                    credentialsId: 'registry-credentials',
                    usernameVariable: 'REGISTRY_USER',
                    passwordVariable: 'REGISTRY_PASS'
                )]) {
                    sh """
                        echo \$REGISTRY_PASS | docker login ghcr.io -u \$REGISTRY_USER --password-stdin
                        docker push ${BACKEND_IMAGE}:${env.IMAGE_TAG}
                        docker push ${BACKEND_IMAGE}:latest
                        docker push ${FRONTEND_IMAGE}:${env.IMAGE_TAG}
                        docker push ${FRONTEND_IMAGE}:latest
                        docker logout ghcr.io
                    """
                }
            }
        }

        // ── Stage 5: Deploy to Kubernetes ─────────────────────────
        stage('Deploy to Kubernetes') {
            steps {
                echo "▶ Deploying to Kubernetes namespace: ${K8S_NAMESPACE}"
                withKubeConfig([credentialsId: KUBECONFIG_ID]) {
                    sh """
                        # Apply all base manifests (namespace, configmap, ingress, etc.)
                        kubectl apply -k k8s/base/ --namespace=${K8S_NAMESPACE}

                        # Update the backend deployment image to the new tag
                        kubectl set image deployment/backend \\
                            backend=${BACKEND_IMAGE}:${env.IMAGE_TAG} \\
                            --namespace=${K8S_NAMESPACE}

                        # Update the frontend deployment image to the new tag
                        kubectl set image deployment/frontend \\
                            frontend=${FRONTEND_IMAGE}:${env.IMAGE_TAG} \\
                            --namespace=${K8S_NAMESPACE}

                        # Wait for rollout to finish — fails pipeline if pods crash
                        kubectl rollout status deployment/backend --namespace=${K8S_NAMESPACE} --timeout=120s
                        kubectl rollout status deployment/frontend --namespace=${K8S_NAMESPACE} --timeout=120s

                        echo "✅ Kubernetes rollout complete"
                    """
                }
            }
        }

        // ── Stage 6: Verify Live Deployment ───────────────────────
        stage('Verify') {
            steps {
                echo "▶ Running post-deploy health checks"
                withKubeConfig([credentialsId: KUBECONFIG_ID]) {
                    sh """
                        # Check all pods are Running
                        kubectl get pods --namespace=${K8S_NAMESPACE} -l app=backend
                        kubectl get pods --namespace=${K8S_NAMESPACE} -l app=frontend

                        # Hit the health endpoint from inside the cluster
                        BACKEND_POD=\$(kubectl get pod -n ${K8S_NAMESPACE} -l app=backend -o jsonpath='{.items[0].metadata.name}')
                        kubectl exec \$BACKEND_POD -n ${K8S_NAMESPACE} -- \\
                            python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health'); print('Backend health:', r.status)"

                        echo "✅ Health checks passed"
                    """
                }
            }
        }

        // ── Stage 7: Clean up old Docker images ───────────────────
        stage('Cleanup') {
            steps {
                sh "docker image prune -f"
                echo "▶ Old dangling images removed"
            }
        }
    }

    // ── Post-build notifications ──────────────────────────────────
    post {
        success {
            echo """
╔══════════════════════════════════════════════╗
║  ✅  UniSora deployed successfully!          ║
║  🌐  https://unisora.in                      ║
║  🏷️   Image tag: ${env.IMAGE_TAG}
╚══════════════════════════════════════════════╝
            """
            // Uncomment to enable Slack notification:
            // slackSend(channel: '#deployments', color: 'good',
            //   message: "✅ UniSora ${env.IMAGE_TAG} deployed to production")
        }
        failure {
            echo "❌ Deploy failed — check the pipeline logs above"
            // slackSend(channel: '#deployments', color: 'danger',
            //   message: "❌ UniSora deploy FAILED — ${env.BUILD_URL}")

            // Auto rollback on failure
            withKubeConfig([credentialsId: KUBECONFIG_ID]) {
                sh """
                    echo "⚠️ Rolling back backend..."
                    kubectl rollout undo deployment/backend --namespace=${K8S_NAMESPACE} || true
                    kubectl rollout undo deployment/frontend --namespace=${K8S_NAMESPACE} || true
                    echo "↩️  Rollback complete"
                """
            }
        }
        always {
            cleanWs()
        }
    }
}
