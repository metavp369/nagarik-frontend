# =============================================================================
# Nagarik - Staging Environment Provider Configuration
# =============================================================================

provider "aws" {
  region = "ap-south-1"

  default_tags {
    tags = {
      Project     = "Nagarik"
      Environment = "staging"
      ManagedBy   = "terraform"
    }
  }
}
