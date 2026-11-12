variable "cluster_name" {
  type    = string
  default = "uptime"
}

variable "node_image" {
  type    = string
  default = "kindest/node:v1.37.0"
}

variable "http_port" {
  description = "port on localhost where the ingress is available"
  type        = number
  default     = 8088
}

variable "traefik_version" {
  type    = string
  default = "42.4.0"
}
