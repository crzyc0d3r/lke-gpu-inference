variable "name" {
  type        = string
  description = "Unique LKE cluster and firewall label prefix."
  default     = "lke-gpu-inference"
}

variable "region" {
  type        = string
  description = "Region offering the selected GPU type."
  default     = "us-sea"
}

variable "kubernetes_version" {
  type        = string
  description = "Currently supported LKE major.minor version; check linode-cli lke versions-list."
}

variable "cpu_type" {
  type    = string
  default = "g6-standard-2"
}

variable "gpu_type" {
  type        = string
  description = "A GPU node with at least 32 GiB RAM and 20 GB VRAM."
  default     = "g2-gpu-rtx4000a1-m"
}

variable "client_cidr" {
  type        = string
  description = "Explicit trusted IPv4 CIDR for endpoint and control-plane access."
  validation {
    condition     = can(cidrnetmask(var.client_cidr)) && var.client_cidr != "0.0.0.0/0"
    error_message = "Provide a trusted IPv4 CIDR, usually your public address with /32."
  }
}

