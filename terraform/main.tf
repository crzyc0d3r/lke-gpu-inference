terraform {
  required_version = ">= 1.5, < 2.0"
  required_providers {
    linode = {
      source  = "linode/linode"
      version = "~> 3.0"
    }
  }
}

provider "linode" {}

resource "linode_firewall" "workers" {
  label           = "${var.name}-workers"
  inbound_policy  = "DROP"
  outbound_policy = "ACCEPT"
  inbound {
    label    = "cluster-tcp"
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "179,5473,10250,10256"
    ipv4     = ["192.168.128.0/17"]
  }
  inbound {
    label    = "cluster-wireguard"
    action   = "ACCEPT"
    protocol = "UDP"
    ports    = "51820"
    ipv4     = ["192.168.128.0/17"]
  }
  inbound {
    label    = "cluster-overlay"
    action   = "ACCEPT"
    protocol = "IPENCAP"
    ipv4     = ["192.168.128.0/17"]
  }
  dynamic "inbound" {
    for_each = toset(["TCP", "UDP"])
    content {
      label    = "nodebalancer-${lower(inbound.value)}"
      action   = "ACCEPT"
      protocol = inbound.value
      ports    = "30000-32767"
      ipv4     = ["192.168.255.0/24"]
    }
  }
}

resource "linode_firewall" "endpoint" {
  label           = "${var.name}-endpoint"
  inbound_policy  = "DROP"
  outbound_policy = "ACCEPT"
  inbound {
    label    = "inference-http"
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "80"
    ipv4     = [var.client_cidr]
  }
}

resource "linode_lke_cluster" "inference" {
  label       = var.name
  region      = var.region
  k8s_version = var.kubernetes_version
  pool {
    type        = var.cpu_type
    count       = 2
    labels      = { workload = "system" }
    firewall_id = linode_firewall.workers.id
  }
  pool {
    type        = var.gpu_type
    count       = 1
    labels      = { workload = "inference" }
    firewall_id = linode_firewall.workers.id
  }
  control_plane {
    acl {
      enabled = true
      addresses {
        ipv4 = [var.client_cidr]
      }
    }
  }
}

output "cluster_id" {
  value = linode_lke_cluster.inference.id
}

output "endpoint_firewall_id" {
  value = linode_firewall.endpoint.id
}

output "kubeconfig" {
  value     = base64decode(linode_lke_cluster.inference.kubeconfig)
  sensitive = true
}

