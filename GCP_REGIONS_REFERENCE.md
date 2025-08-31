# GCP Regions Reference

This document shows GCP regions and their corresponding locations. Use this to understand what locations are available for each region.

## North America

| Region | Location | Country |
|--------|----------|---------|
| us-east1 | South Carolina | US |
| us-east4 | Northern Virginia | US |
| us-central1 | Iowa | US |
| us-central2 | Los Angeles | US |
| us-west1 | Oregon | US |
| us-west2 | Los Angeles | US |
| us-west3 | Salt Lake City | US |
| us-west4 | Las Vegas | US |
| northamerica-northeast1 | Montréal | CA |
| northamerica-northeast2 | Toronto | CA |

## Europe

| Region | Location | Country |
|--------|----------|---------|
| europe-west1 | Belgium | BE |
| europe-west2 | London | GB |
| europe-west3 | Frankfurt | DE |
| europe-west4 | Netherlands | NL |
| europe-west5 | Zürich | CH |
| europe-west6 | Finland | FI |
| europe-west8 | Milan | IT |
| europe-west9 | Paris | FR |
| europe-west10 | Berlin | DE |
| europe-west12 | Turin | IT |
| europe-central2 | Warsaw | PL |
| europe-north1 | Finland | FI |
| europe-southwest1 | Madrid | ES |

## Asia Pacific

| Region | Location | Country |
|--------|----------|---------|
| asia-east1 | Taiwan | TW |
| asia-east2 | Hong Kong | HK |
| asia-northeast1 | Tokyo | JP |
| asia-northeast2 | Osaka | JP |
| asia-northeast3 | Seoul | KR |
| asia-south1 | Mumbai | IN |
| asia-south2 | Delhi | IN |
| asia-southeast1 | Singapore | SG |
| asia-southeast2 | Jakarta | ID |
| australia-southeast1 | Sydney | AU |
| australia-southeast2 | Melbourne | AU |

## Other Regions

| Region | Location | Country |
|--------|----------|---------|
| southamerica-east1 | São Paulo | BR |
| southamerica-west1 | Santiago | CL |
| me-west1 | Tel Aviv | IL |
| africa-south1 | Johannesburg | ZA |

## Notes

- **Multiple locations per region**: Some regions like `us-central2` and `us-west2` both map to Los Angeles
- **Country mapping**: Each region maps to a specific country for CloudFront geo restrictions
- **Your clusters**: Check your `cluster_regions.json` to see which regions you're using 