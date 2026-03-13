# =============================================================================
# Nagarik - Dev Environment Backend Configuration
# =============================================================================

terraform {
  backend "s3" {
    bucket         = "Nagarik-terraform-state"
    key            = "env/dev/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "Nagarik-terraform-lock"
    encrypt        = true
  }
}
