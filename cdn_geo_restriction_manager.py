#!/usr/bin/env python3
"""
CloudFront Distribution Region Checker

This script takes a CloudFront distribution ID as input and retrieves
the allowed/blocked regions for that CDN distribution.

Usage:
    python cdn_region_checker.py <distribution_id>
    python cdn_region_checker.py --list-distributions
    python cdn_region_checker.py --config <config_file>
"""

import json
import sys
import argparse
import boto3
import requests
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional, Tuple, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CloudFrontGeoRestrictionManager:
    def __init__(self, config_file: str = "config.json"):
        """Initialize the CloudFront geo restriction manager with configuration."""
        self.config_file = config_file
        self.config = self._load_config()
        self.clients = self._initialize_clients()
        self.country_codes = self._load_country_codes()
        self.cluster_regions = self._load_cluster_regions()
        
    def _load_config(self) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {self.config_file}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_file} not found")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            sys.exit(1)

    def _initialize_clients(self) -> Dict[str, boto3.client]:
        """Initialize AWS clients for each account."""
        clients = {}
        for account in self.config.get('aws_accounts', []):
            try:
                # Validate required fields
                required_fields = ['account_name', 'access_key_id', 'secret_access_key', 'region']
                missing_fields = [field for field in required_fields if field not in account or not account[field]]
                
                if missing_fields:
                    logger.error(f"Missing required fields for account {account.get('account_name', 'Unknown')}: {missing_fields}")
                    continue
                
                # Prepare client parameters
                client_params = {
                    'service_name': 'cloudfront',
                    'region_name': account['region']
                }
                
                # Add credentials
                if 'session_token' in account and account['session_token']:
                    # Use temporary credentials with session token
                    client_params.update({
                        'aws_access_key_id': account['access_key_id'],
                        'aws_secret_access_key': account['secret_access_key'],
                        'aws_session_token': account['session_token']
                    })
                else:
                    # Use permanent credentials
                    client_params.update({
                        'aws_access_key_id': account['access_key_id'],
                        'aws_secret_access_key': account['secret_access_key']
                    })
                
                # Create the client
                client = boto3.client(**client_params)
                clients[account['account_name']] = client
                logger.info(f"✅ Initialized client for account: {account['account_name']}")
                    
            except KeyError as e:
                logger.error(f"❌ Missing configuration field for account {account.get('account_name', 'Unknown')}: {e}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize client for {account.get('account_name', 'Unknown')}: {e}")
        
        return clients

    def get_distribution_info(self, distribution_id: str) -> Optional[Dict]:
        """Get distribution information for a given distribution ID."""
        if not distribution_id or not distribution_id.strip():
            logger.error("Distribution ID is empty or invalid")
            return None
            
        for account_name, client in self.clients.items():
            try:
                logger.info(f"Checking distribution {distribution_id} in account {account_name}")
                response = client.get_distribution(Id=distribution_id)
                
                if 'Distribution' not in response:
                    logger.error(f"Invalid response format from AWS for distribution {distribution_id}")
                    continue
                    
                return {
                    'account': account_name,
                    'distribution': response['Distribution']
                }
                
            except ClientError as e:
                error_code = e.response['Error'].get('Code', 'Unknown')
                if error_code == 'NoSuchDistribution':
                    logger.warning(f"Distribution {distribution_id} not found in account {account_name}")
                    continue
                elif error_code == 'AccessDenied':
                    logger.error(f"Access denied for distribution {distribution_id} in account {account_name}")
                    continue
                elif error_code == 'InvalidArgument':
                    logger.error(f"Invalid distribution ID format: {distribution_id}")
                    return None
                else:
                    logger.error(f"AWS error accessing distribution in {account_name}: {error_code} - {e}")
                    continue
            except Exception as e:
                logger.error(f"Unexpected error in account {account_name}: {e}")
                continue
        
        return None

    def get_geo_restrictions(self, distribution_info: Dict) -> Dict:
        """Extract geo restrictions from distribution information."""
        distribution = distribution_info['distribution']
        config = distribution['DistributionConfig']
        
        # Debug: Print all top-level keys in the config
        logger.info(f"Distribution config keys: {list(config.keys())}")
        
        # Check for distribution-level geo restrictions (Security tab)
        distribution_geo_restrictions = config.get('GeoRestrictions', {})
        
        # Debug: Check if GeoRestrictions exists
        if 'GeoRestrictions' in config:
            logger.info(f"Found GeoRestrictions: {config['GeoRestrictions']}")
        else:
            logger.info("No GeoRestrictions found in config")
            
        # Check the Restrictions field (this is where geo restrictions are usually stored)
        if 'Restrictions' in config:
            restrictions = config['Restrictions']
            logger.info(f"Found Restrictions: {restrictions}")
            
            # Check for GeoRestriction in Restrictions
            if 'GeoRestriction' in restrictions:
                geo_restriction = restrictions['GeoRestriction']
                logger.info(f"Found GeoRestriction in Restrictions: {geo_restriction}")
                distribution_geo_restrictions = geo_restriction
        else:
            logger.info("No Restrictions field found")
            
        # Also check if there are any other geo-related fields
        geo_related_keys = [key for key in config.keys() if 'geo' in key.lower() or 'location' in key.lower()]
        if geo_related_keys:
            logger.info(f"Found geo-related keys: {geo_related_keys}")

        return {
            'distribution_level': distribution_geo_restrictions
        }

    def _load_country_codes(self) -> Dict[str, str]:
        """Load country code mappings from JSON file."""
        try:
            with open('country_codes.json', 'r') as f:
                data = json.load(f)
                return data.get('country_codes', {})
        except FileNotFoundError:
            logger.warning("country_codes.json not found, using country codes only")
            return {}
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in country_codes.json: {e}, using country codes only")
            return {}
        except Exception as e:
            logger.warning(f"Error loading country codes: {e}, using country codes only")
            return {}

    def format_geo_restrictions(self, geo_restrictions: Dict) -> str:
        """Format geo restrictions in a readable format."""
        try:
            result = []
            
            # Load country code mappings
            country_codes = self.country_codes
            
            # Distribution-level geo restrictions (Security tab)
            distribution_restrictions = geo_restrictions.get('distribution_level', {})
            if distribution_restrictions:
                restriction_type = distribution_restrictions.get('RestrictionType', 'N/A')
                items = distribution_restrictions.get('Items', [])
                
                # Convert country codes to names, fallback to codes if mapping missing
                country_names = []
                for item in items:
                    country_name = country_codes.get(item, item)  # Fallback to code if name not found
                    country_names.append(country_name)
                
                if restriction_type == 'whitelist':
                    result.append(f"ALLOWED Countries: {', '.join(country_names)}")
                elif restriction_type == 'blacklist':
                    result.append(f"BLOCKED Countries: {', '.join(country_names)}")
                else:
                    result.append("No geo restrictions")
            else:
                result.append("No geo restrictions")

            return '\n'.join(result) if result else "No geo restrictions found"
            
        except Exception as e:
            logger.error(f"Error formatting geo restrictions: {e}")
            return "Error: Unable to format geo restrictions"

    def list_distributions(self) -> List[str]:
        """List all distribution IDs from configuration."""
        return self.config.get('distribution_ids', [])

    def check_distribution(self, distribution_id: str) -> str:
        """Main method to check a distribution's geo restrictions."""
        try:
            logger.info(f"Checking distribution: {distribution_id}")
            
            # Get distribution information
            distribution_info = self.get_distribution_info(distribution_id)
            if not distribution_info:
                return f"❌ Distribution {distribution_id} not found in any configured AWS account"
            
            # Extract geo restrictions
            geo_restrictions = self.get_geo_restrictions(distribution_info)
            
            # Get distribution details with error handling
            try:
                domain_name = distribution_info['distribution'].get('DomainName', 'Unknown')
                status = distribution_info['distribution'].get('Status', 'Unknown')
            except KeyError as e:
                logger.error(f"Missing required distribution field: {e}")
                domain_name = "Unknown"
                status = "Unknown"
            
            # Format the results
            result = f"""
Distribution ID: {distribution_id}
Account: {distribution_info['account']}
Domain Name: {domain_name}
Status: {status}

Geo Restrictions:
{self.format_geo_restrictions(geo_restrictions)}
"""
            return result, distribution_info, geo_restrictions
            
        except Exception as e:
            logger.error(f"Unexpected error checking distribution {distribution_id}: {e}")
            return f"❌ Error checking distribution {distribution_id}: {str(e)}", None, None

    def _load_country_codes_reverse(self) -> Dict[str, str]:
        """Load reverse country code mappings (name to code)."""
        try:
            with open('country_codes.json', 'r') as f:
                data = json.load(f)
                country_codes = data.get('country_codes', {})
                # Create reverse mapping
                return {v.lower(): k for k, v in country_codes.items()}
        except Exception:
            return {}

    def _load_cluster_regions(self) -> Dict[str, Any]:
        """Load cluster regions configuration."""
        try:
            with open('cluster_regions.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️  Warning: cluster_regions.json not found")
            return {"aws_eks_clusters": {}, "gcp_gke_clusters": {}}
        except json.JSONDecodeError:
            print("❌ Error: Invalid JSON in cluster_regions.json")
            return {"aws_eks_clusters": {}, "gcp_gke_clusters": {}}

    def get_channel_delivery_details(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Fetch channel delivery details from StormForge API."""
        # Get StormForge configuration from config
        stormforge_config = self.config.get('stormforge', {})
        api_token = stormforge_config.get('api_token')
        base_url = stormforge_config.get('base_url', 'https://stormforge.tsv3.amagi.tv/v1')
        
        if not api_token:
            print("❌ Error: StormForge API token not found in config.json")
            print("   💡 Add StormForge configuration to config.json:")
            print("   {")
            print('     "stormforge": {')
            print('       "api_token": "YOUR_STORMFORGE_API_TOKEN",')
            print('       "base_url": "https://stormforge.tsv3.amagi.tv/v1"')
            print("     }")
            print("   }")
            return None
            
        url = f"{base_url}/tsdelivery/{channel_id}"
        headers = {
            'Authorization': f'Bearer {api_token}'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching channel details: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON response: {e}")
            return None

    def extract_setup_values(self, data: Any, setup_values: List[str] = None) -> List[str]:
        """Recursively extract all 'setup' values from JSON data."""
        if setup_values is None:
            setup_values = []
            
        if isinstance(data, dict):
            for key, value in data.items():
                if key == 'setup' and isinstance(value, str):
                    setup_values.append(value)
                elif isinstance(value, (dict, list)):
                    self.extract_setup_values(value, setup_values)
        elif isinstance(data, list):
            for item in data:
                self.extract_setup_values(item, setup_values)
                
        return setup_values

    def get_regions_for_setups(self, setup_values: List[str]) -> Dict[str, List[str]]:
        """Get regions for given setup values from cluster configuration."""
        regions = {"aws": [], "gcp": []}
        found_setups = []
        not_found_setups = []
        
        # Check AWS EKS clusters
        for cluster_name, cluster_info in self.cluster_regions.get("aws_eks_clusters", {}).items():
            if cluster_name in setup_values:
                region = cluster_info.get("region")
                if region:
                    regions["aws"].append(region)
                    found_setups.append(cluster_name)
        
        # Check GCP GKE clusters (handle both with and without -gke suffix)
        for cluster_name, cluster_info in self.cluster_regions.get("gcp_gke_clusters", {}).items():
            # Try exact match first
            if cluster_name in setup_values:
                region = cluster_info.get("region")
                if region:
                    regions["gcp"].append(region)
                    found_setups.append(cluster_name)
            else:
                # Try matching without -gke suffix (e.g., ts-us-e1-n2 matches ts-us-e1-n2-gke)
                base_name = cluster_name.replace("-gke", "")
                if base_name in setup_values:
                    region = cluster_info.get("region")
                    if region:
                        regions["gcp"].append(region)
                        found_setups.append(f"{base_name} (mapped to {cluster_name})")
        
        # Find setups that weren't found in any cluster configuration
        for setup in setup_values:
            if setup not in found_setups and not any(setup in found for found in found_setups):
                not_found_setups.append(setup)
        
        # Store results for reporting
        self.found_setups = found_setups
        self.not_found_setups = not_found_setups
                    
        return regions

    def get_countries_for_regions(self, regions: Dict[str, List[str]]) -> List[str]:
        """Get countries directly from cluster_regions.json country field."""
        countries = []
        found_locations = []
        missing_country_clusters = []
        
        # Extract countries directly from cluster_regions.json
        for cloud_type, region_list in regions.items():
            for region in region_list:
                # Find clusters that use this region
                if cloud_type == "aws":
                    clusters = self.cluster_regions.get("aws_eks_clusters", {})
                else:  # gcp
                    clusters = self.cluster_regions.get("gcp_gke_clusters", {})
                
                # Get country directly from cluster info
                for cluster_name, cluster_info in clusters.items():
                    if cluster_info.get("region") == region:
                        location = cluster_info.get("location")
                        country = cluster_info.get("country")
                        
                        if location and country:
                            found_locations.append(f"{region} ({location})")
                            if country not in countries:
                                countries.append(country)
                        elif location and not country:
                            # Found cluster but missing country code
                            missing_country_clusters.append(f"{cluster_name} ({location})")
                        elif not location:
                            # Missing location info
                            missing_country_clusters.append(f"{cluster_name} (no location)")
        
        # Store found locations and missing country info for reporting
        self.found_locations = found_locations
        self.missing_country_clusters = missing_country_clusters
                    
        return countries

    def check_channel_whitelist_status(self, channel_id: str, distribution_id: str) -> None:
        """Check if countries for channel's setup regions are whitelisted."""
        print(f"\n🔍 Checking whitelist status for channel: {channel_id}")
        print("=" * 60)
        
        # Get channel delivery details
        delivery_details = self.get_channel_delivery_details(channel_id)
        if not delivery_details:
            print("❌ Could not fetch channel delivery details")
            return
            
        # Extract setup values
        setup_values = self.extract_setup_values(delivery_details)
        if not setup_values:
            print("❌ No setup values found in delivery details")
            return
            
        print(f"📍 Found setup values: {', '.join(setup_values)}")
        
        # Get regions for setups
        regions = self.get_regions_for_setups(setup_values)
        
        # Show found setups and mappings
        if hasattr(self, 'found_setups') and self.found_setups:
            print(f"✅ Found setups in cluster config: {', '.join(self.found_setups)}")
        
        # Show warnings for not found setups
        if hasattr(self, 'not_found_setups') and self.not_found_setups:
            print(f"⚠️  WARNING: Setups not found in cluster config: {', '.join(self.not_found_setups)}")
            print("   💡 These setups might be:")
            print("      - New clusters not yet added to cluster_regions.json")
            print("      - Different naming convention (e.g., ts-us-e1-n2 vs ts-us-e1-n2-gke)")
            print("      - Clusters in different regions")
        
        print(f"📍 AWS Regions: {', '.join(regions['aws']) if regions['aws'] else 'None'}")
        print(f"📍 GCP Regions: {', '.join(regions['gcp']) if regions['gcp'] else 'None'}")
        
        # Get countries for regions
        countries = self.get_countries_for_regions(regions)
        
        # Show location details
        if hasattr(self, 'found_locations') and self.found_locations:
            print(f"📍 Found locations: {', '.join(self.found_locations)}")
        
        # Show warnings for missing country codes
        if hasattr(self, 'missing_country_clusters') and self.missing_country_clusters:
            print(f"⚠️  WARNING: Clusters missing country codes: {', '.join(self.missing_country_clusters)}")
            print("   💡 Add 'country' field to these clusters in cluster_regions.json:")
            print("      Example: {\"region\": \"us-east1\", \"location\": \"South Carolina\", \"country\": \"US\"}")
        
        if not countries:
            if hasattr(self, 'not_found_setups') and self.not_found_setups:
                print("❌ Could not map regions to countries - no setups found in cluster config")
                print("   💡 Please check your cluster_regions.json file and ensure all setups are mapped")
            elif hasattr(self, 'missing_country_clusters') and self.missing_country_clusters:
                print("❌ Could not map regions to countries - missing country codes in cluster config")
                print("   💡 Please add 'country' field to clusters in cluster_regions.json")
            else:
                print("❌ Could not map regions to countries")
            return
            
        print(f"📍 Required countries: {', '.join(countries)}")
        
        # Get current CloudFront restrictions
        try:
            distribution_info = self.get_distribution_info(distribution_id)
            if not distribution_info:
                print("❌ Could not get distribution info")
                return
                
            geo_restrictions = self.get_geo_restrictions(distribution_info)
            formatted_restrictions = self.format_geo_restrictions(geo_restrictions)
            
            print(f"\n📍 Current CloudFront restrictions:")
            print(f"   {formatted_restrictions}")
            
            # Check if required countries are whitelisted
            if 'distribution_level' in geo_restrictions:
                dist_restrictions = geo_restrictions['distribution_level']
                restriction_type = dist_restrictions.get('RestrictionType', 'none')
                allowed_countries = dist_restrictions.get('Items', [])
                
                if restriction_type == 'whitelist':
                    missing_countries = [country for country in countries if country not in allowed_countries]
                    if missing_countries:
                        print(f"\n⚠️  WARNING: Missing countries from whitelist: {', '.join(missing_countries)}")
                        print("💡 Consider adding these countries to ensure proper access")
                    else:
                        print(f"\n✅ All required countries are whitelisted!")
                elif restriction_type == 'blacklist':
                    blocked_countries = [country for country in countries if country in allowed_countries]
                    if blocked_countries:
                        print(f"\n⚠️  WARNING: Required countries are blacklisted: {', '.join(blocked_countries)}")
                        print("💡 Consider removing these countries from blacklist")
                    else:
                        print(f"\n✅ No required countries are blacklisted!")
                else:
                    print(f"\n✅ No restrictions - all countries have access")
                    
        except Exception as e:
            print(f"❌ Error checking CloudFront restrictions: {e}")

    def interactive_modify_restrictions(self, distribution_info: Dict, geo_restrictions: Dict):
        """Interactive menu to modify geo restrictions."""
        print("\n" + "="*60)
        print("🔧 INTERACTIVE GEO RESTRICTIONS MODIFIER")
        print("="*60)
        
        # Get current restrictions
        distribution_restrictions = geo_restrictions.get('distribution_level', {})
        current_type = distribution_restrictions.get('RestrictionType', 'none')
        current_items = distribution_restrictions.get('Items', [])
        
        # Load country mappings
        country_codes = self.country_codes
        reverse_codes = self._load_country_codes_reverse()
        
        while True:
            print(f"\n📍 Current Restriction Type: {current_type.upper()}")
            if current_items:
                country_names = [country_codes.get(item, item) for item in current_items]
                print(f"📍 Current Countries: {', '.join(country_names)}")
            else:
                print("📍 Current Countries: None")
            
            print("\nOptions:")
            print("1. Add country to list")
            print("2. Remove country from list")
            print("3. Remove all restrictions")
            print("4. Exit and apply changes")
            print("5. Exit without changes")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                self._add_country_to_list(current_items, country_codes, reverse_codes)
            elif choice == '2':
                self._remove_country_from_list(current_items, country_codes)
            elif choice == '3':
                current_items = []
                current_type = 'none'
                print("✅ All restrictions cleared")
            elif choice == '4':
                # Show summary of changes before applying
                print("\n" + "="*60)
                print("📋 CHANGES SUMMARY")
                print("="*60)
                print(f"Restriction Type: {current_type.upper()}")
                if current_items:
                    country_names = [country_codes.get(item, item) for item in current_items]
                    print(f"Countries: {', '.join(country_names)}")
                else:
                    print("Countries: None (no restrictions)")
                
                print(f"\nDistribution: {distribution_info['distribution']['Id']}")
                print(f"Domain: {distribution_info['distribution']['DomainName']}")
                
                # Ask for confirmation
                confirm = input("\n⚠️  Do you want to apply these changes to CloudFront? (yes/no): ").strip().lower()
                
                if confirm in ['yes', 'y']:
                    print("🔄 Applying changes to CloudFront...")
                    if self._apply_changes_to_cloudfront(distribution_info, current_type, current_items):
                        print("✅ Changes applied successfully!")
                        break
                    else:
                        print("❌ Failed to apply changes")
                else:
                    print("❌ Changes cancelled")
            elif choice == '5':
                print("❌ Exiting without changes")
                break
            else:
                print("❌ Invalid choice. Please enter 1-5.")

    def _add_country_to_list(self, current_items: List[str], country_codes: Dict, reverse_codes: Dict):
        """Add a country to the current restriction list."""
        print("\n🌍 Available countries (enter country name or code):")
        
        # Show some common countries
        common_countries = ['US', 'GB', 'IN', 'SG', 'MY', 'CA', 'AU', 'DE', 'FR', 'JP']
        for code in common_countries:
            name = country_codes.get(code, code)
            print(f"  {code} - {name}")
        
        print("  ... (or enter any country name/code)")
        
        country_input = input("\nEnter country to add: ").strip().upper()
        
        if not country_input:
            print("❌ No country entered")
            return
        
        # Try to find the country code
        country_code = None
        
        # Direct code match
        if country_input in country_codes:
            country_code = country_input
        # Name to code match
        elif country_input.lower() in reverse_codes:
            country_code = reverse_codes[country_input.lower()]
        else:
            print(f"❌ Country '{country_input}' not found. Please use a valid country code.")
            return
        
        if country_code in current_items:
            print(f"❌ {country_codes.get(country_code, country_code)} is already in the list")
        else:
            country_name = country_codes.get(country_code, country_code)
            confirm = input(f"⚠️  Add {country_name} ({country_code}) to list? (yes/no): ").strip().lower()
            
            if confirm in ['yes', 'y']:
                current_items.append(country_code)
                print(f"✅ Added {country_name} ({country_code}) to the list")
            else:
                print("❌ Addition cancelled")

    def _remove_country_from_list(self, current_items: List[str], country_codes: Dict):
        """Remove a country from the current restriction list."""
        if not current_items:
            print("❌ No countries in the list to remove")
            return
        
        print("\n🌍 Current countries:")
        for i, code in enumerate(current_items, 1):
            name = country_codes.get(code, code)
            print(f"  {i}. {name} ({code})")
        
        try:
            choice = input("\nEnter country name/code to remove: ").strip()
            
            if not choice:
                print("❌ No country entered")
                return
            
            # Try to find the country
            country_to_remove = None
            
            # Check by code
            if choice.upper() in current_items:
                country_to_remove = choice.upper()
            # Check by name
            else:
                for code in current_items:
                    name = country_codes.get(code, code)
                    if choice.lower() in name.lower():
                        country_to_remove = code
                        break
            
            if country_to_remove:
                country_name = country_codes.get(country_to_remove, country_to_remove)
                confirm = input(f"⚠️  Remove {country_name} ({country_to_remove}) from list? (yes/no): ").strip().lower()
                
                if confirm in ['yes', 'y']:
                    current_items.remove(country_to_remove)
                    print(f"✅ Removed {country_name} ({country_to_remove}) from list")
                else:
                    print("❌ Removal cancelled")
            else:
                print(f"❌ Country '{choice}' not found in current list")
                
        except ValueError:
            print("❌ Please enter a valid country name or code")

    def _change_restriction_type(self, current_type: str) -> str:
        """Change the restriction type between allow list and block list."""
        print("Select restriction type:")
        print("1. Allow List (whitelist) - Only listed countries can access")
        print("2. Block List (blacklist) - Listed countries are blocked")
        print("3. No Restrictions - All countries can access")
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == '1':
            new_type = 'whitelist'
            print("✅ Set to Allow List (whitelist)")
        elif choice == '2':
            new_type = 'blacklist'
            print("✅ Set to Block List (blacklist)")
        elif choice == '3':
            new_type = 'none'
            print("✅ Set to No Restrictions")
        else:
            print("❌ Invalid choice. Keeping current type.")
            new_type = current_type
        
        return new_type

    def _apply_changes_to_cloudfront(self, distribution_info: Dict, restriction_type: str, items: List[str]) -> bool:
        """Apply the changes to CloudFront distribution."""
        try:
            # Get the client for this account
            account_name = distribution_info['account']
            client = self.clients.get(account_name)
            
            if not client:
                print(f"❌ No client found for account {account_name}")
                return False
            
            # Get current distribution config
            distribution = distribution_info['distribution']
            config = distribution['DistributionConfig'].copy()
            
            # Update geo restrictions
            if restriction_type == 'none':
                # Remove restrictions
                if 'Restrictions' in config:
                    if 'GeoRestriction' in config['Restrictions']:
                        del config['Restrictions']['GeoRestriction']
                    if not config['Restrictions']:
                        del config['Restrictions']
            else:
                # Add/update restrictions
                if 'Restrictions' not in config:
                    config['Restrictions'] = {}
                
                config['Restrictions']['GeoRestriction'] = {
                    'RestrictionType': restriction_type,
                    'Quantity': len(items),
                    'Items': items
                }
            
            # Update the distribution
            distribution_id = distribution['Id']
            
            # Get the current ETag by fetching the distribution again
            try:
                current_dist = client.get_distribution(Id=distribution_id)
                etag = current_dist['ETag']
            except Exception as e:
                print(f"❌ Error getting current ETag: {e}")
                return False
            
            response = client.update_distribution(
                Id=distribution_id,
                DistributionConfig=config,
                IfMatch=etag
            )
            
            print(f"✅ Distribution {distribution_id} updated successfully")
            return True
            
        except ClientError as e:
            error_code = e.response['Error'].get('Code', 'Unknown')
            if error_code == 'PreconditionFailed':
                print("❌ ETag mismatch - distribution was modified by another process")
                print("   Please try again")
            elif error_code == 'AccessDenied':
                print("❌ Access denied - check your CloudFront permissions")
            elif error_code == 'InvalidArgument':
                print("❌ Invalid configuration - check your geo restrictions")
            else:
                print(f"❌ AWS error: {error_code} - {e}")
            return False
        except Exception as e:
            print(f"❌ Error updating distribution: {e}")
            return False


def main():
    """Main function to handle command line arguments and execute the script."""
    parser = argparse.ArgumentParser(
        description="Check CloudFront distribution geo restrictions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cdn_region_checker.py E1234567890ABCD
  python cdn_region_checker.py --list-distributions
  python cdn_region_checker.py --config my_config.json E1234567890ABCD
        """
    )
    
    parser.add_argument(
        'distribution_id',
        nargs='?',
        help='CloudFront distribution ID to check'
    )
    
    parser.add_argument(
        '--config',
        default='config.json',
        help='Path to configuration file (default: config.json)'
    )
    
    parser.add_argument(
        '--list-distributions',
        action='store_true',
        help='List all distribution IDs from configuration'
    )
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Enable interactive mode to modify geo restrictions'
    )
    
    parser.add_argument(
        '--channel-id',
        help='Channel ID to check setup regions and whitelist status'
    )
    
    args = parser.parse_args()
    
    # Initialize the checker with proper error handling
    try:
        checker = CloudFrontGeoRestrictionManager(args.config)
    except FileNotFoundError:
        print("❌ ERROR: Configuration file not found!")
        print(f"   Please create '{args.config}' with your AWS credentials")
        print("   Example:")
        print("   {")
        print('     "aws_accounts": [{')
        print('       "account_name": "My Account",')
        print('       "access_key_id": "YOUR_ACCESS_KEY",')
        print('       "secret_access_key": "YOUR_SECRET_KEY",')
        print('       "region": "us-east-1"')
        print("     }]")
        print("   }")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in configuration file: {e}")
        print("   Please check your config.json format")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize CloudFront checker: {e}")
        sys.exit(1)
    
    # Check if any AWS clients were initialized
    if not checker.clients:
        print("❌ ERROR: No AWS accounts configured or all failed to initialize!")
        print("   Please check your AWS credentials in config.json")
        print("   Common issues:")
        print("   - Invalid access key or secret key")
        print("   - Expired session tokens")
        print("   - Incorrect region")
        print("   - Network connectivity issues")
        sys.exit(1)
    
    # Handle different modes
    if args.list_distributions:
        try:
            distributions = checker.list_distributions()
            if distributions:
                print("✅ Configured Distribution IDs:")
                for dist_id in distributions:
                    print(f"  - {dist_id}")
            else:
                print("ℹ️  No distribution IDs found in configuration")
        except Exception as e:
            print(f"❌ ERROR: Failed to list distributions: {e}")
            sys.exit(1)
    
    elif args.distribution_id:
        # Validate distribution ID format
        if not args.distribution_id.strip():
            print("❌ ERROR: Distribution ID cannot be empty!")
            print("   Usage: python cdn_geo_restriction_manager.py E1234567890ABCD")
            sys.exit(1)
        
        if not args.distribution_id.startswith('E'):
            print("❌ ERROR: Invalid distribution ID format!")
            print("   Distribution ID should start with 'E' (e.g., E1234567890ABCD)")
            sys.exit(1)
        
        try:
            # If channel ID is provided, check whitelist status for channel
            if args.channel_id:
                checker.check_channel_whitelist_status(args.channel_id, args.distribution_id)
            else:
                result = checker.check_distribution(args.distribution_id)
                
                # Check if result is a tuple (interactive mode data)
                if isinstance(result, tuple):
                    output, distribution_info, geo_restrictions = result
                    print(output)
                    
                    # If interactive mode is enabled, show the modification menu
                    if args.interactive:
                        if distribution_info and geo_restrictions:
                            checker.interactive_modify_restrictions(distribution_info, geo_restrictions)
                        else:
                            print("❌ Cannot enter interactive mode - distribution not found or error occurred")
                else:
                    # Regular output (error message)
                    print(result)
                
        except KeyboardInterrupt:
            print("\n⚠️  Operation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"❌ ERROR: Failed to check distribution: {e}")
            sys.exit(1)
    
    else:
        print("❌ ERROR: No distribution ID provided!")
        print("   Usage: python cdn_region_checker.py E1234567890ABCD")
        print("   Use --help for more options")
        sys.exit(1)


if __name__ == "__main__":
    main() 