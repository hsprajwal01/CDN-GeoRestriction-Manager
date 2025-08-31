# CloudFront Geo Restriction Manager - User Guide

## 🎯 What This Tool Does

This tool helps you manage CloudFront geo restrictions. You can:
- View which countries are allowed/blocked
- Add countries to allow or block list
- Remove countries from the list
- Remove all restrictions

**Use Case:** If your cluster is hosted in Mumbai (ap-south-1) but CloudFront doesn't have India in the whitelist, use this tool to add India for proper access.

## 🚀 How to Use

### Step 1: View Current Restrictions
```bash
python cdn_geo_restriction_manager.py YOUR_DISTRIBUTION_ID
```

### Step 2: Modify Restrictions (Interactive)
```bash
python cdn_geo_restriction_manager.py YOUR_DISTRIBUTION_ID --interactive
```

### Step 3: Check Channel Whitelist Status
```bash
python cdn_geo_restriction_manager.py YOUR_DISTRIBUTION_ID --channel-id YOUR_CHANNEL_ID
```

This checks if countries for your channel's setup regions are whitelisted in CloudFront.

## 🔧 Interactive Mode Flow

When you run with `--interactive`, you'll see this menu:

```
🔧 INTERACTIVE GEO RESTRICTIONS MODIFIER
============================================================

📍 Current Restriction Type: WHITELIST
📍 Current Countries: India, Singapore, Malaysia, United States, United Kingdom

Options:
1. Add country to list
2. Remove country from list
3. Remove all restrictions
4. Exit and apply changes
5. Exit without changes
```

### Option 1: Add Country
- Enter country name or code (e.g., `Canada` or `CA`)
- Tool asks for confirmation
- Country gets added to current list

### Option 2: Remove Country
- Enter country name or code to remove
- Tool asks for confirmation
- Country gets removed from current list

### Option 3: Remove All Restrictions
- Clears all countries from the list
- Sets to "No Restrictions"

### Option 4: Exit and Apply Changes
- Shows summary of all your changes
- Asks for confirmation
- Applies changes to CloudFront

### Option 5: Exit Without Changes
- Exits without making any changes

## 🌍 Your Cluster Information

Based on your `cluster_regions.json`, you have these clusters:

### AWS EKS Clusters
- **Ohio (us-east-2)**: `ts-us-e2-n1`, `ts-us-e2-n2`
- **Oregon (us-west-2)**: `ts-us-w2-n1`
- **Mumbai (ap-south-1)**: `ts-ap-s1-n1`
- **Ireland (eu-west-1)**: `ts-eu-w1-n2`

### GCP GKE Clusters
- **Belgium (europe-west1)**: `ts-eu-w1-new-gke`
- **South Carolina (us-east1)**: `ts-us-e1-n1-gke`, `ts-us-e1-n2-gke`, `ts-us-roku-gke`

## 📝 Example Usage

### Example 1: Add Countries 
```bash
# Start interactive mode
python cdn_geo_restriction_manager.py E36F0LSULI2ABO --interactive

# Choose option 1: Add country to list
# Add: US, CA, MX (for US clusters)
# Add: GB, DE, FR (for EU clusters)
# Add: IN, SG, MY (for Asia cluster)

# Choose option 4: Exit and apply changes
# Confirm: yes
```

### Example 2: Use Case - Mumbai Cluster Access
If your cluster is hosted in Mumbai (ap-south-1) but CloudFront doesn't have India in the whitelist:

```bash
# Check current restrictions
python cdn_geo_restriction_manager.py E36F0LSULI2ABO

# If India is not in the allowed list, add it:
python cdn_geo_restriction_manager.py E36F0LSULI2ABO --interactive

# Choose option 1: Add country to list
# Enter: India (or IN)
# Confirm: yes
# Choose option 4: Exit and apply changes
# Confirm: yes
```

This ensures users in India can access your content served from the Mumbai cluster.

### Example 3: Remove a Country
```bash
# Start interactive mode
python cdn_geo_restriction_manager.py E36F0LSULI2ABO --interactive

# Choose option 2: Remove country from list
# Enter: US
# Confirm: yes

# Choose option 4: Exit and apply changes
# Confirm: yes
```

### Example 4: Remove All Restrictions
```bash
# Start interactive mode
python cdn_geo_restriction_manager.py E36F0LSULI2ABO --interactive

# Choose option 3: Remove all restrictions
# Choose option 4: Exit and apply changes
# Confirm: yes
```

### Example 5: Check Channel Whitelist Status
```bash
# Check if countries for channel's setup regions are whitelisted
python cdn_geo_restriction_manager.py E36F0LSULI2ABO --channel-id amg00353-lionsgatetvfast-moviesphere-fawesomeus
```

This will:
1. Fetch channel delivery details from StormForge API
2. Extract setup values (e.g., "ts-us-e1-n2")
3. Map setups to regions and countries (handles GKE naming like "ts-us-e1-n2" → "ts-us-e1-n2-gke")
4. Check if those countries are whitelisted in CloudFront
5. Show warnings for setups not found in cluster configuration

## 🚨 Common Issues

**"Distribution not found"**
- Check your distribution ID in CloudFront console

**"Access denied"**
- Check your AWS credentials have CloudFront permissions

**"ETag mismatch"**
- Try again (distribution was modified elsewhere)

**"Country not found"**
- Use valid country codes like US, GB, IN, etc.

**"Setups not found in cluster config"**
- Add missing setups to cluster_regions.json
- Check naming conventions (e.g., "ts-us-e1-n2" vs "ts-us-e1-n2-gke")
- Verify cluster regions are correctly mapped

**"Clusters missing country codes"**
- Add "country" field to clusters in cluster_regions.json
- Example: `{"region": "us-east1", "location": "South Carolina", "country": "US"}`

**"StormForge API token not found"**
- Add StormForge configuration to config.json
- Include api_token and base_url in stormforge section

## 📁 Additional Files

- **`cluster_regions.json`** - Contains your AWS EKS and GCP GKE cluster names with their regions and locations
- **`country_codes.json`** - Complete mapping of country codes (US, GB, IN) to full country names
- **`config.json`** - AWS credentials and StormForge API token configuration

## 🎯 Tips

1. Always review the summary before applying changes
