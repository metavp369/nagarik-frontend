provider "aws" {
  region = "ap-south-1"

  default_tags {
    tags = {
      Project   = "Nagarik"
      ManagedBy = "terraform"
    }
  }
}
