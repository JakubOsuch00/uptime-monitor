resource "kind_cluster" "this" {
  name            = var.cluster_name
  node_image      = var.node_image
  wait_for_ready  = true
  kubeconfig_path = "${path.module}/${var.cluster_name}-config"

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"

      # traefik listens on nodePort 30080, this exposes it on localhost
      extra_port_mappings {
        container_port = 30080
        host_port      = var.http_port
      }
    }

    node {
      role = "worker"
    }
  }
}

provider "helm" {
  kubernetes = {
    host                   = kind_cluster.this.endpoint
    client_certificate     = kind_cluster.this.client_certificate
    client_key             = kind_cluster.this.client_key
    cluster_ca_certificate = kind_cluster.this.cluster_ca_certificate
  }
}

resource "helm_release" "traefik" {
  name             = "traefik"
  repository       = "https://traefik.github.io/charts"
  chart            = "traefik"
  version          = var.traefik_version
  namespace        = "traefik"
  create_namespace = true

  values = [yamlencode({
    service = { spec = { type = "NodePort" } }
    ports = {
      web       = { nodePort = 30080 }
      websecure = { expose = { default = false } }
    }
    ingressClass = { enabled = true, isDefaultClass = true }
  })]
}
