# CloudFront Distribution Geo Restriction Manager

A tool to check and modify geo restrictions for AWS CloudFront distributions.

## 📋 Requirements

- Python 3.7 or higher
- AWS credentials with CloudFront permissions
- CloudFront distribution ID

## 🚀 Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

Create `config.json`:

```json
{
  "aws_accounts": [
    {
      "account_name": "Production",
      "access_key_id": "YOUR_ACCESS_KEY_ID",
      "secret_access_key": "YOUR_SECRET_ACCESS_KEY",
      "region": "us-east-1"
    }
  ],
  "stormforge": {
    "api_token": "YOUR_STORMFORGE_API_TOKEN",
    "base_url": "https://stormforge.tsv3.amagi.tv/v1"
  }
}
```

### 3. Required AWS Permissions
- `cloudfront:GetDistribution`
- `cloudfront:UpdateDistribution`

## 🎯 Usage

### View Geo Restrictions
```bash
python cdn_geo_restriction_manager.py E1234567890ABCD
```

### Interactive Mode (Modify Restrictions)
```bash
python cdn_geo_restriction_manager.py E1234567890ABCD --interactive
```

### Check Channel Whitelist Status
```bash
python cdn_geo_restriction_manager.py E1234567890ABCD --channel-id YOUR_CHANNEL_ID
```

## 📖 User Guide

See `USER_GUIDE.md` for detailed usage instructions.

## 📁 Additional Files

- **`cluster_regions.json`** - Cluster names and their regions/locations
- **`country_codes.json`** - Country code to country name mappings

## 🚨 Common Issues

- **"Configuration file not found"** → Create `config.json` with AWS credentials
- **"Access denied"** → Check CloudFront permissions
- **"Distribution not found"** → Verify distribution ID
- **"ETag mismatch"** → Try again (distribution modified elsewhere)

