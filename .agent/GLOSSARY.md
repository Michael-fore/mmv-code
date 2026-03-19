# MMV Domain Glossary

> Abbreviations and domain terms used throughout the codebase. Read this when you encounter an unfamiliar term.

---

## Property / Appraisal

| Term | Definition |
|------|-----------|
| **CAD** | County Appraisal District — the Texas county agency that values all property for tax purposes |
| **HCAD** | Harris County Appraisal District — the CAD for Harris County (Houston area); largest data source |
| **TCAD** | Travis County Appraisal District — Austin area |
| **Account number** | CAD's unique ID for a property parcel within a county. PK pattern: `(county, account_number)` |
| **SPTB code** | State Property Tax Board classification code. Determines `property_type` field. |
| **F1** | SPTB code → Commercial real estate (office, retail, etc.) |
| **F2** | SPTB code → Industrial |
| **B1 / B2** | SPTB code → Multifamily residential |
| **L1** | SPTB code → Commercial personal property |
| **A** | SPTB code → Single-family residential |
| **D / E** | SPTB codes → Agricultural land |
| **Legal description** | Formal written description of a property's boundaries as recorded in the deed |
| **Appraised value** | CAD's estimate of market value for tax purposes (not necessarily what it would sell for) |
| **Assessed value** | The taxable portion of appraised value after any exemptions (homestead, etc.) |
| **Improvement value** | Value of structures on the land (building_value in schema) |
| **Extra features** | Above-ground improvements that aren't the primary building (pools, fences, etc.) |

---

## Transactions / Deeds

| Term | Definition |
|------|-----------|
| **Deed** | Legal instrument transferring property ownership |
| **Grantor** | Seller / party transferring the property |
| **Grantee** | Buyer / party receiving the property |
| **Consideration** | Sale price (may be $0 for non-arm's-length: gifts, family transfers, foreclosures) |
| **Arm's-length transaction** | Sale between unrelated parties at fair market value |
| **Warranty deed** | Most common deed type — seller guarantees clear title |
| **Quitclaim deed** | Transfers whatever interest the grantor has; no title guarantee |
| **Instrument number** | County recorder's ID for a recorded document |
| **Volume / Page** | Old-style deed book reference (pre-digital recording) |

---

## Flooding / Risk

| Term | Definition |
|------|-----------|
| **FEMA** | Federal Emergency Management Agency — issues flood maps |
| **NFHL** | National Flood Hazard Layer — FEMA's GIS dataset of flood zones |
| **SFHA** | Special Flood Hazard Area — areas with ≥1% annual flood chance; mandatory insurance for federally-backed loans |
| **Flood zone AE** | High-risk SFHA zone with a base flood elevation established |
| **Flood zone X** | Low-to-moderate risk zone (outside SFHA) |
| **Flood zone VE** | Coastal high-hazard area (wave action + flooding) |
| **BFE** | Base Flood Elevation — the 100-year flood elevation in feet above sea level |

---

## Agriculture

| Term | Definition |
|------|-----------|
| **USDA NASS** | National Agricultural Statistics Service — publishes land values, cash rents, crop production |
| **USDA FSA** | Farm Service Agency — administers CRP, farm loans |
| **USDA FAS** | Foreign Agricultural Service — publishes export data |
| **USDA NRCS** | Natural Resources Conservation Service — soil survey (SSURGO) |
| **SSURGO** | Soil Survey Geographic Database — detailed soil data by county |
| **CRP** | Conservation Reserve Program — USDA program paying farmers to not farm environmentally sensitive land |
| **Cash rent** | Annual rent paid by a tenant farmer to a landowner ($/acre/year) |
| **Cap rate** | Net operating income ÷ asset value (%). Lower = more expensive relative to income |
| **CAGR** | Compound Annual Growth Rate — annualized growth rate over a period |

---

## Commercial Real Estate

| Term | Definition |
|------|-----------|
| **CRE** | Commercial Real Estate — includes office, retail, industrial, multifamily |
| **NOI** | Net Operating Income — gross revenue minus operating expenses (before debt service) |
| **DSCR** | Debt Service Coverage Ratio — NOI ÷ annual debt payments. ≥1.25 typically required for financing |
| **Cap rate** | In CRE: NOI ÷ purchase price. E.g., 5% cap rate = $1M NOI on a $20M building |
| **NNN (triple net)** | Lease structure where tenant pays base rent + taxes + insurance + maintenance |
| **PSF** | Per Square Foot — standard unit for office/retail lease rates and sale prices |
| **Absorption** | Net change in leased space over a period (sqft). Positive = market tightening |
| **Vacancy rate** | % of total rentable space that is unoccupied |
| **Sale comp** | Comparable sale — a recent transaction used to estimate current market value |
| **TAMU** | Texas A&M Real Estate Center — publishes Texas CRE market statistics |

---

## Entities / Corporate

| Term | Definition |
|------|-----------|
| **LLC** | Limited Liability Company — common ownership vehicle for real estate |
| **LP** | Limited Partnership |
| **REIT** | Real Estate Investment Trust — publicly traded company owning real estate |
| **SIC** | Standard Industrial Classification — 4-digit code identifying industry type |
| **CIK** | Central Index Key — SEC's unique ID for a registrant |
| **Accession number** | SEC's unique ID for a specific filing |
| **10-K** | Annual report filed with the SEC |
| **10-Q** | Quarterly report filed with the SEC |
| **8-K** | Current report for material events (acquisitions, executive changes, etc.) |

---

## GCP / Infrastructure

| Term | Definition |
|------|-----------|
| **Cloud SQL Proxy** | Binary that creates an encrypted tunnel to Cloud SQL; required for all local DB connections |
| **Cloud Run Job** | GCP serverless batch job container (`mmv-backfill`) |
| **Cloud Scheduler** | GCP cron service — triggers Cloud Run Jobs on a schedule |
| **GCS** | Google Cloud Storage — raw file storage (`gs://mmv-raw/`) |
| **IAM** | Identity and Access Management — GCP permissions system |
| **ADC** | Application Default Credentials — GCP's credential discovery chain |
| **Service account key** | JSON file granting GCP access (`~/mmv-cloud-llm-agent-key.json`) |

---

## Geospatial

| Term | Definition |
|------|-----------|
| **EPSG:4326** | WGS84 — standard lat/lon coordinate system (used in all MMV data) |
| **EPSG:2278** | Texas State Plane South Central (US survey feet) — raw HCAD GIS data projection; reprojected on ingest |
| **GeoJSON** | JSON format for geographic features (points, polygons, etc.) |
| **Centroid** | Geometric center point of a polygon (parcel) |
| **FIPS** | Federal Information Processing Standard — numeric codes for states/counties (e.g., Harris = 48201) |
