output "kubeconfig" {
  description = "export KUBECONFIG=<this> to use kubectl with the cluster"
  value       = abspath(kind_cluster.this.kubeconfig_path)
}

output "url" {
  value = "http://uptime.localhost:${var.http_port}"
}
