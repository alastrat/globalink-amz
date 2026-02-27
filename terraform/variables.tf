variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "droplet_name" {
  description = "Name of the droplet"
  type        = string
  default     = "globalink-fba"
}

variable "droplet_size" {
  description = "Droplet size slug"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "droplet_region" {
  description = "Droplet region"
  type        = string
  default     = "nyc1"
}

variable "deploy_ssh_public_key" {
  description = "SSH public key for GitHub Actions deploy"
  type        = string
}

variable "allowed_ssh_ips" {
  description = "IP addresses allowed to SSH (CIDR notation)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "alert_email" {
  description = "Email for monitoring alerts"
  type        = string
}

variable "spaces_region" {
  description = "Region for DO Spaces bucket"
  type        = string
  default     = "nyc3"
}
